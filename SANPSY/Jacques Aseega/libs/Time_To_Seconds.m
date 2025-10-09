function [res] = Time_To_Seconds(time)
%TIME_TO_SECONDS Conversion de'une chaine de caractère représentant l'heure en secondes
% Split the time string into hours, minutes, and seconds
timeParts = strsplit(time, ':');

% Convert hours, minutes, and seconds to numbers
hours = str2double(timeParts{1});
minutes = str2double(timeParts{2});
seconds = str2double(timeParts{3});

% Calculate the total seconds
res = (hours * 3600) + (minutes * 60) + seconds;
end

