addpath('libs');

dataPath = 'Datas';						% Chemin du dossier principal contenant les sous-dossiers
electrods = {'C3', 'C4', 'F3', 'F4'};	% Liste des Electrodes Utiles

% Création du sous-dossier "Spindles" dans le dataPath s'il n'existe pas déjà
spindlesFolderPath = fullfile(dataPath, 'Spindles');
if ~isfolder(spindlesFolderPath)
	mkdir(spindlesFolderPath);
end

disp('Récupération de la liste des fichiers')
files = Get_Files(dataPath, electrods);	% Récupération des fichiers triés par sujets
subjects = fieldnames(files);			% Récupération des noms des sujets (clés de la structure)

% Parcourir les sujets
for i = 1:length(subjects)
	subject = subjects{i};				% Obtenez le nom du sujet actuel
	disp(['Sujet ', subject])
	
	subjectMat = [];

	% Obtenez les fichiers associés au sujet actuel
	subjectFiles = files.(subject);
	
	% Parcourir les fichiers associés au sujet actuel
	for j = 1:length(subjectFiles)
		file = subjectFiles{j};
		elec = strsplit(file, '.');
		elec = elec{2};						% Récupération du nom de l'électrode
		parse_mat = Parsing_Spindles(file);	% Récupération des fuseaux (tableaux de 8 colonnes et N lignes contenant des valeurs nnumériques
		% Ajout de la colonne électrode avec la valeur elec dedans (une chaine de caractères)
		numSpindles = size(parse_mat, 1);
		switch elec
			case 'C3'
				e = 0;
			case 'C4'
				e = 1;
			case 'F3'
				e = 2;
			case 'F4'
				e = 3;
			otherwise
				e = 4;
		end
		elecColumn = repmat(e, numSpindles, 1);
		cycleColumn = zeros(numSpindles, 1);
		
		% Ajout de la colonne Cycle avec rien dedans (ou 0 si rien n'est pas possible)
		% Ajout du tableau à la meta matrice du sujet
		% Ajouter la colonne électrod avec la valeur elec dedans (une chaîne de caractères)
		% Ajouter la colonne Cycle avec rien dedans (ou 0 si rien n'est pas possible)
		
		% Concaténer les tableaux des spindles avec les colonnes "Electrod" et "Cycle"
		spindleDataWithInfo = [parse_mat, elecColumn, cycleColumn];
		subjectMat = [subjectMat; spindleDataWithInfo];
	end
	% Enregistrement de la Meta Matrice du sujet dans un fichier csv dans dataPath + subject + ' Spindles.csv'
	% Enregistrement de la Meta Matrice du sujet dans un fichier csv
	% Le nom du fichier aura la forme : 'subject Spindles.csv'
	outputFile = fullfile(spindlesFolderPath, [subject, ' Spindles.csv']);
	writematrix(subjectMat, outputFile);
end

