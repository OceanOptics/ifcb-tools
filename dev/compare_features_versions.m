% Compare features v2 with features v4 from Heidi's IFCB_analysis
% created: Nov 12, 2019
% author: Nils

%% Load data 
v2 = load('/Users/nils/Data/NAAMES/IFCB/archived/ifcb_v13_20190613.mat'); v2 = v2.ifcb;
v4 = load('/Users/nils/Data/NAAMES/IFCB/IFCB_NAAMES_20191111.mat'); v4 = v4.ifcb;

%% Compare v2 vs v4 samples
fprintf('Samples missing from v4:\n');
n = 0;
for i=1:height(v2)
  if ~any(strcmp(v4.BinId, v2.id{i}))
    fprintf('\tN%d  %s\t%s\n', v2.campaign_id(i), v2.type(i), v2.id{i});
    n = n + 1;
  end
end
if n == 0; fprintf('\tNone\n'); end
fprintf('Samples added in v4:\n');
for i=1:height(v4)
  if ~any(strcmp(v2.id, v4.BinId{i}))
    fprintf('\tN%d  %s\t%s\n', v4.Campaign(i), v4.Type(i), v4.BinId{i});
  end
end
% => recovered more samples in v4
% => remove culture samples from v2 for fair comparison
v2(v2.type == 'culture',:) = [];

%% Build table with all cells
% taxon_level = 'Taxon';
taxon_level = 'Group';
metric = 'Biovolume';
% metric = 'Area';
% metric = 'EquivalentDiameter';
% V4
n = sum(cellfun(@length, v4.ImageId));
v4s = table(cell(n,1), NaN(n,1), 'VariableNames', {'Class', 'Value'});
k = 1;
for i=progress(1:height(v4))
  sel = v4.AnnotationStatus{i} == 'validated';
  n = sum(sel);
  v4s.Class(k:k+n-1) = cellstr(v4.(taxon_level){i}(sel));
  v4s.Value(k:k+n-1) = v4.(metric){i}(sel);
  k = k + n;
end
v4s(k:end,:) = [];
v4s.Class = categorical(v4s.Class);
%% V2
switch taxon_level
  case 'Taxon'
    v2_taxon_level = 'Species';
  case 'Group'
    v2_taxon_level = 'Groups';
end
switch metric
  case 'EquivalentDiameter'
    v2_metric = 'ESDA';
  otherwise
    v2_metric = metric;
end
n = sum(cellfun(@length, v2.ROIid));
v2s = table(cell(n,1), NaN(n,1), 'VariableNames', {'Class', 'Value'});
k = 1;
for i=progress(1:height(v2))
  if isempty(v2.AnnotationStatus{i}); continue; end
  sel = v2.AnnotationStatus{i} == 'validated';
  n = sum(sel);
  v2s.Class(k:k+n-1) = cellstr(v2.(v2_taxon_level){i}(sel));
  v2s.Value(k:k+n-1) = v2.(v2_metric){i}(sel);
  k = k + n;
end
v2s(k:end,:) = [];
v2s.Class = categorical(v2s.Class);

%% Plots :)
y_lim = [0 2000];
fig(1);

subplot(2,1,1);
title('Features v2');
boxplot(v2s.Value, v2s.Class);
ylabel(metric); xtickangle(45);
ylim(y_lim);

subplot(2,1,2);
title('Features v4');
boxplot(v4s.Value, v4s.Class);
ylabel(metric); xtickangle(45);
ylim(y_lim);

savefig(['/Users/nils/Data/NAAMES/IFCB/Figures/bp_fvc_' metric '_' taxon_level '.fig']);
save_fig(['/Users/nils/Data/NAAMES/IFCB/Figures/bp_fvc_' metric '_' taxon_level '.png'], 1200, 800);

%% Plots
v2_group = {'Artefact','Chloro','Chryso','Cilliate','Crypto','Cyanobacteria','Diatom','Dinoflagellate','Eugleno','Not living','Other','Prymnesio','Rhizaria','Zoo'};
v4_group = {'Artefact','Chlorophyte','Chrysophyte','Cilliate','Cryptophyte','Cyanobacterium','Diatom','Dinoflagellate','Euglenoid','Not living','Other','Prymnesiophyte','Rhizaria','Zoo'};
for i = 1:length(v2_class)
% i=1
  fig(2); 
  subplot(1,2,1);
  boxplot(v2s.Value(v2s.Class == v2_group{i}), {v2_group{i}});
  y_lim = [0 prctile(v2s.Value(v2s.Class == v2_group{i}),90)];
  ylim(y_lim); ylabel(metric); title(sprintf('v2 median=%.2f', nanmedian(v2s.Value(v2s.Class == v2_group{i}))));
  subplot(1,2,2);
  boxplot(v4s.Value(v4s.Class == v4_group{i}), {v4_group{i}});
  ylim(y_lim); ylabel(metric); title(sprintf('v4 median=%.2f', nanmedian(v4s.Value(v4s.Class == v4_group{i}))));
  set(gca,'YAxisLocation', 'right');
  save_fig(['/Users/nils/Data/NAAMES/IFCB/Figures/bp_fvc_' metric '_' taxon_level '_' v4_group{i} '.png'], 400, 400);
end
