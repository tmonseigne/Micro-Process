function cell2csv(fileName, cellArray, separator)
% cell2csv Write cell array content into a *.csv file.
% 
% cell2csv(fileName, cellArray, separator)
% 
% fileName:  Name of the file to save. It must have the '.csv' extension.
% cellArray: Cell array to be saved. 
% separator: (Optional) Separator for the CSV file. Default is ','.
% 
% Example:
% >> data = {'Name', 'Age', 'Gender'; 'John', 28, 'Male'; 'Lisa', 22, 'Female'};
% >> cell2csv('data.csv', data);

    if nargin < 3
        separator = ',';
    end

    [rows, cols] = size(cellArray);

    fileID = fopen(fileName, 'w');
    for i = 1:rows
        for j = 1:cols
            % Ensure each cell is a string
            if ~ischar(cellArray{i, j})
                cellArray{i, j} = num2str(cellArray{i, j});
            end
            % Write the cell content with the separator
            fprintf(fileID, '%s', cellArray{i, j});
            if j < cols
                fprintf(fileID, separator);
            end
        end
        fprintf(fileID, '\n');
    end

    fclose(fileID);
end
