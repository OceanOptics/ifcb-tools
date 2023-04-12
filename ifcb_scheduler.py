####!/usr/bin/python3
"""
Schedule execution start and end of IFCB Acquire

IFCB Acquire must be set with:
    + Auto Start On
    + Samples: 1
    + To not start on boot

MIT License
Author: Nils Haentjens
Updated: April 2023
"""
import configparser
import logging
import os
import sched
import signal
import subprocess
import sys
from datetime import datetime, timedelta, date
from datetime import time as dtime
from threading import Thread
from time import time, sleep


__version__ = '0.0.1'


logger = logging.getLogger('ifcb.scheduler')
IFCB_ACQUIRE_EXE = '/home/ifcb/IFCBacquire/gLauncher/IFCBacquire.Gtk'
# IFCB_ACQUIRE_EXE = 'ls'  # Dummy for test
IFCB_ACQUIRE_PROCESS_NAME = b'IFCBacquire.Gtk'


ifcb_acquire_process = None


def kill_ifcb_acquire():
    """
    Look for ifcb acquire instance in the list of processes and kill them if any found
    This function is useful when the process was lost or started from outside this script
    """
    try:
        p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
        out, err = p.communicate()
        for line in out.splitlines():
            if IFCB_ACQUIRE_PROCESS_NAME in line:
                pid = int(line.split(None, 1)[0])
                os.kill(pid, signal.SIGKILL)
    except Exception as e:
        logger.critical(f'Kill ifcb acquire failed: {e}')


def start_ifcb_acquire():
    """
    Start IFCB Acquire
    """
    global ifcb_acquire_process
    # Kill previous instance running
    kill_ifcb_acquire()
    sleep(5)
    # Start IFCB Acquire
    ifcb_acquire_process = subprocess.Popen(IFCB_ACQUIRE_EXE)
    logger.debug('Started IFCB acquire.')


def stop_ifcb_acquire():
    """
    Stop IFCB Acquire instance
    """
    global ifcb_acquire_process
    if ifcb_acquire_process is not None:
        if ifcb_acquire_process.poll() is not None:
            logger.info('IFCB acquire already stopped.')
            return
        ifcb_acquire_process.send_signal(signal.SIGINT)  # Recommended to send ctrl+c in log of IFCB Acquire
        try:
            ifcb_acquire_process.wait(5)
            logger.debug('Stopped IFCB acquire.')
        except subprocess.TimeoutExpired:
            logger.error('Stop IFCB acquire gracefully failed. Killing process now.')
            ifcb_acquire_process.kill()


class Scheduler:
    def __init__(self, filename):
        self.start_minutes, self.acq_length, self.legs = [], None, []
        self._scheduled_day = None
        self.read_configuration(filename)
        self._scheduler = sched.scheduler(time, sleep)
        self._thread = None
        self._alive = False

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

    @property
    def is_alive(self):
        return False if self._thread is None else self._thread.is_alive()

    def start(self):
        if not self._alive:
            self._alive = True
            self._thread = Thread(name=repr(self), target=self._run)
            self._thread.daemon = True
            self._thread.start()

    def stop(self):
        if self._alive:
            self._alive = False

    def join(self, timeout=None):
        if self._thread is not None:
            self._thread.join(timeout)

    def _run(self):
        logger.info("Scheduler running ...")
        while self._alive:
            # Schedule acquisition for the day
            today = date.today()
            if self._scheduled_day != today:
                self._scheduled_day = today
                self.make_schedule_of_day()
            # Run non-blocking schedule
            deadline = self._scheduler.run(blocking=False)
            sleep(1 if deadline is None else min(1, deadline))

    def read_configuration(self, filename):
        if not os.path.isfile(path_to_cfg):
            logger.error(f"Configuration file not found {path_to_cfg}. Exiting.")
            raise FileNotFoundError(f"Configuration file not found {path_to_cfg}.")
        cfg = configparser.ConfigParser()
        cfg.read(filename)
        self.start_minutes = [int(m) for m in cfg.get('DEFAULT', 'AcquisitionStartMinutes', fallback='15,45').split(',')]
        self.acq_length = timedelta(minutes=cfg.getint('DEFAULT', 'AcquisitionLengthMinutes',  fallback=29))
        self.legs = []
        for leg in [s for s in cfg.sections() if s.startswith('leg.')]:
            self.legs.append((
                datetime.fromisoformat(cfg.get(leg, 'StartDateTime')),
                datetime.fromisoformat(cfg.get(leg, 'StopDateTime'))
            ))
            logger.info(f"  + leg '{leg[4:]}' from {self.legs[-1][0]} to {self.legs[-1][1]}")

    def make_schedule_of_day(self):
        """
        Create schedule and add it to scheduler.
        Important: should only be called once per day as it will replicate the schedule otherwise
        """
        # Get acquisition times for today
        today = date.today()
        acquisition_day, time_start, time_stop = False, dtime(0, 0, 0), None
        for leg in self.legs:
            leg_start_date, leg_stop_date = leg[0].date(), leg[1].date()
            if leg_start_date <= today and today <= leg_stop_date:
                if leg[0].date() == today:
                    time_start = leg[0].time()
                if leg_stop_date == today:
                    time_stop = leg[1].time()
                acquisition_day = True
                break
        if not acquisition_day:
            logger.info(f'No acquisition scheduled today {today}.')
            return
        # Add to schedule
        c = 0
        # Start with latest between right now and time_start to prevent scheduling past events
        dt = datetime.combine(today, max(time_start, datetime.now().time()))
        while dt <= datetime.combine(today, dtime(23, 59, 59, 999999)):
            # Add events at requested minutes of the hour
            for start_minute in self.start_minutes:
                dt_start = dt.replace(minute=start_minute, second=0, microsecond=0)
                dt_stop = dt_start + self.acq_length
                if time_stop is not None and dt_stop.time() > time_stop:
                    logger.info(f'Scheduled {c} acquisition(s) today {today}.')
                    # return
                if time_start <= dt_start.time():
                    self._scheduler.enterabs(dt_start.timestamp(), 2, start_ifcb_acquire)
                    self._scheduler.enterabs(dt_stop.timestamp(), 1, stop_ifcb_acquire)
                    c+=1
            # Go to next hours
            dt += timedelta(hours=1)
        logger.info(f'Scheduled {c} acquisition(s) today {today}.')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s [%(name)s]  %(message)s")  # filename='ifcb_scheduler.log'
    logger.info(f"IFCB acquire scheduler v{__version__}")
    path_to_cfg = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ifcb_scheduler_cfg.ini')
    if len(sys.argv) < 2:
        logger.info(f"Default to {os.path.basename(path_to_cfg)} configuration.")
    elif not os.path.isfile(sys.argv[1]):
        logger.info(f"File {os.path.basename(sys.argv[1])} not found. "
                    f"Default to {os.path.basename(path_to_cfg)} configuration.")
    # Set Scheduler with configuration
    try:
        s = Scheduler(path_to_cfg)
    except FileNotFoundError:
        sys.exit(-1)
    s.start()
    try:
        while True:
            sleep(10)
    except KeyboardInterrupt:
        logger.info('Stopping IFCB scheduler ... ')
    finally:
        s.stop()
        s.join()
