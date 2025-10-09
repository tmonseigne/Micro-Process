addpath('libs');

dataPath = 'Datas';						% Chemin du dossier principal contenant les sous-dossiers

% Création du sous-dossier "Spindles" dans le dataPath s'il n'existe pas déjà
cyclesFolderPath = fullfile(dataPath, 'Cycles');

disp('Récupération de la liste des fichiers')

files =  dir(fullfile(cyclesFolderPath, '*.mat'));
files = Sort_Files_By_Subjects(cyclesFolderPath, files);
subjects = fieldnames(files);			% Récupération des noms des sujets (clés de la structure)

metaMat = [];

% Parcourir les sujets
for i = 1:length(subjects)
	subject = subjects{i};				% Obtenez le nom du sujet actuel
	subjecti = str2double(extractAfter(subject, 3));
	disp(['Sujet ', subject])
 	
 	file = files.(subject){1};
	data = load(file);
	% Récupération de l'heure de début / fin de l'enregistrement
	start_record = Time_To_Seconds(data.aseega_analysis.info.recording.orig_start_time);
	duration_record = Time_To_Seconds(data.aseega_analysis.info.recording.orig_duration);
	if start_record + duration_record > 86400 % 24 * 3600
		start_record = start_record - 86400;
	end
	% Récupération des cycles avec leur temps de début / fin
	% Calcul de leur positions début / fin
	% Ajout de la ligne à la méta matrice
	% numéro de cycle (0 pour dire nuit complète), postion de début, Durée, Position de fin
 	metaMat = [metaMat; [subjecti, 0, start_record, duration_record, start_record + duration_record]];
	
	cycles = data.aseega_analysis.sleepparams.sleep_onset_1.sleep_cycles.cycle;
	for j = 1:length(cycles)
		cycle = cycles{j};
		start_t = Time_To_Seconds(cycle.start_t) - start_record;
		if start_t > 86400 % 24 * 3600
			start_t = start_t - 86400;
		end
		end_t =  Time_To_Seconds(cycle.end_t) - start_record ; 
		metaMat = [metaMat; [subjecti, j, start_t, Time_To_Seconds(cycle.duration), end_t]];
	end
end

outputFile = fullfile(dataPath, 'Cycles.csv');
writematrix(metaMat, outputFile);
