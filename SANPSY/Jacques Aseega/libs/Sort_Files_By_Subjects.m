function [res] = Sort_Files_By_Subjects(path, files)
%SORT_FILES_BY_SUBJECTS Ajouter à un tableau/structure ou autre les fichiers triées par leur nom de sujet
res = struct();
% Parcourir les fichiers .mat
for j = 1:length(files)
	nomFichier = files(j).name;
	cheminFichier = fullfile(path, nomFichier);
	nomDuSujet = Get_Subject(nomFichier);
	
	% Vérifier si le sujet existe déjà dans la structure
	if isfield(res, nomDuSujet)
		% Ajouter le fichier à la liste existante
		res.(nomDuSujet) = [res.(nomDuSujet), cheminFichier];
	else
		% Créer une nouvelle entrée dans la structure pour ce sujet
		res.(nomDuSujet) = {cheminFichier};
	end
end
end

