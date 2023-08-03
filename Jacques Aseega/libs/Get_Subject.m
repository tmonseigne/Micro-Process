function [res] = Get_Subject(filename)
%GET_SUBJECT Extraire le nom du sujet à partir du nom du fichier
% Supposons que le nom du fichier est de la forme "nom_du_sujet.electrode.A4R.mat"
% et que vous souhaitez extraire "nom_du_sujet"
res = strsplit(filename, '.');
res = res{1};
end

