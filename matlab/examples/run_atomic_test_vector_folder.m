function results = run_atomic_test_vector_folder(configDir, outputRoot, seed)
%RUN_ATOMIC_TEST_VECTOR_FOLDER Run all atomic raw-burst configs in a folder.

    arguments
        configDir (1,:) char
        outputRoot (1,:) char
        seed (1,1) double = 1234
    end

    listing = dir(fullfile(configDir, '*.json'));
    listing = listing(~[listing.isdir]);
    [~, order] = sort({listing.name});
    listing = listing(order);

    if ~exist(outputRoot, 'dir')
        mkdir(outputRoot);
    end

    results = repmat(struct('configPath', "", 'status', "", 'error', "", 'outputBase', ""), 1, numel(listing));
    for i = 1:numel(listing)
        configPath = fullfile(listing(i).folder, listing(i).name);
        stem = erase(string(listing(i).name), ".json");
        caseDir = fullfile(outputRoot, stem);
        if ~exist(caseDir, 'dir')
            mkdir(caseDir);
        end

        try
            cfg = jsondecode(fileread(configPath));
            if ~isfield(cfg, 'generationParameters')
                cfg.generationParameters = struct();
            end
            cfg.generationParameters.seed = seed;
            cfg.generationParameters.outputFolder = caseDir;
            cfg.generationParameters.outputBase = char(stem + "_matlab");
            tmpPath = fullfile(caseDir, stem + "_tmp.json");
            fid = fopen(tmpPath, 'w');
            assert(fid >= 0, 'Failed to open temporary config file for writing');
            fprintf(fid, '%s', jsonencode(cfg));
            fclose(fid);

            summary = run_atomic_test_vector(tmpPath);
            results(i) = struct( ...
                'configPath', string(configPath), ...
                'status', "ok", ...
                'error', "", ...
                'outputBase', string(summary.outputBase));
        catch ME
            results(i) = struct( ...
                'configPath', string(configPath), ...
                'status', "error", ...
                'error', string(getReport(ME, 'basic', 'hyperlinks', 'off')), ...
                'outputBase', "");
        end
    end

    summaryPath = fullfile(outputRoot, 'summary.json');
    fid = fopen(summaryPath, 'w');
    fprintf(fid, '%s', jsonencode(results, 'PrettyPrint', true));
    fclose(fid);
    fprintf('Wrote folder summary to %s\n', summaryPath);
end
