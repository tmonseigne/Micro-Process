function [res] = Get_Files(path, electrods)
%GET_FILES Summary of this function goes here Detailed explanation goes here

% Obtenez la liste des dossiers dans le dossier principal
folders = dir(path);
folders = folders([folders.isdir]); % Supprimez les éléments qui ne sont pas des dossiers

% Créer une structure pour stocker les fichiers triés par nom de sujet
res = struct();

% Parcourir les dossiers
for i = 1:length(folders)
	folderName = folders(i).name;
	
	% Ignorer les dossiers spéciaux '.' et '..'
	if strcmp(folderName, '.') || strcmp(folderName, '..')
		continue;
	end
	
	% Vérifier si la partie centrale du nom du dossier est une lettre autorisée
	if numel(folderName) ~= 20
		continue;
	end
	elec = folderName(19:20); % Supposant que le format est "numerical-results-XX", alors l'élecrtode est à l'index 19 et 20
	if ~ismember(elec, electrods)
		continue;
	end
	
	% Obtenir le chemin complet du dossier actuel
	folderPath = fullfile(path, folderName);
	
	% Obtenez la liste des fichiers .mat dans le dossier actuel
	fichiersMat = dir(fullfile(folderPath, '*.mat'));
	
	% Ajouter à un tableau/structure ou autre les fichiers triées par leur nom de sujet (le nom du fichier est de la forme nom du sujet.electrode.A4R.mat
	% Parcourir les fichiers .mat
	for j = 1:length(fichiersMat)
		nomFichier = fichiersMat(j).name;
		cheminFichier = fullfile(folderPath, nomFichier);
		
		% Extraire le nom du sujet à partir du nom du fichier
		% Supposons que le nom du fichier est de la forme "nom_du_sujet.electrode.A4R.mat"
		% et que vous souhaitez extraire "nom_du_sujet"
		nomDuSujet = strsplit(nomFichier, '.');
		nomDuSujet = nomDuSujet{1};
		
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
end

