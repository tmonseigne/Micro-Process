function [Res] = Parsing_Spindles(file)
%Parsing_Spindles Summary of this function goes here Detailed explanation goes here

data = load(file);							% Lecture du fichier (.mat)
s = data.aseega_analysis.micro.spindles;	% Accès à la structure puis sous structures du fichier -> aseega_analysis -> micro -> spindles
% Création du tableau | Position | Duration | Power | Frequency | Frequential Instability  | frequential_purity  | Temporal Instability | Maximum Amplitude |
% Combiner les tableaux dans la sous structure spindles chacun étant de la forme 1xN avec le même N pour tous
Res = transpose([s.position; s.duration; s.power; s.frequency; s.frequential_instability; s.frequential_purity; s.temporal_instability; s.maximum_amplitude]);
end


