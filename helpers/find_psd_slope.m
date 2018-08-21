function [slope, intercept, psd, bin_means] = find_psd_slope(esd, bin_edges)
% FIND_PSD_SLOPE Compute PSD and find its slope
%
% INPUT:
%   ESD <Nx1 double> Equivalent Spherical Diameter (um)
%   bin_edges <1xM double> edges of each size bin (um)
%   
% OUTPUT:
%   slope <double> Slope of the PSD
%   PSD <1x(M-1) double> Particle Size Distribution
%
% Example of plot:
%   plot(bin_means, psd, 's', bin_means, x1(1)*(5./bin_means).^x1(2));
%
% author: Nils (based on Alison Chase code)
% created: May 16, 2018

% Optional input
if nargin < 2
  % Cover full IFCB size range (um)
%   dlim = [2 200]; n = 10;
  % Cover good IFCB size range (um)
  dlim = [5 80]; n = 6;
  % Compute log distributed bin edges
  q=exp(1/n*log(dlim(2)/dlim(1)));
  bin_edges = dlim(1)*q.^(0:n);
end
bin_means = (bin_edges(2:end) + bin_edges(1:end-1)) / 2;

% Compute PSD
psd = NaN(1,size(bin_edges,2)-1);
for k=1:(size(bin_edges,2)-1)
  psd(k) = sum(bin_edges(k) <= esd & esd < bin_edges(k+1)) ...
           / (bin_edges(k+1) - bin_edges(k));
end

% Find Slope
opts = optimset('fminsearch');
opts = optimset(opts,'MaxIter',4000);
opts = optimset(opts,'MaxFunEvals',2000);
opts = optimset(opts,'TolFun',1e-9);
x0=[100, 4];
x1 = fminsearch(@least_squares,x0,opts,psd,bin_means);
slope = x1(2);
intercept = x1(1);

end

function y = least_squares(x0,psd,bin)
% Fits a power-law function to a spectra.
% Assume uncertainties are the same for all wavelengths.
y = sum((psd - x0(1).*(5./bin).^x0(2)).^2);
end