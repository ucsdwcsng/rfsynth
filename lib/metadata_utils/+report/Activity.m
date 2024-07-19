classdef Activity < handle
    % This class is used to store the list of activity types.
    % 
    % .. list-table::
    %    :widths: 10 90
    %    :header-rows: 1
    %
    %    * - Signal
    %      - Description
    %    * - :class:`+report.Activity.overt_baseline`
    %      - Overt baseline
    %    * - :class:`+report.Activity.overt_new`
    %      - Overt new
    %    * - :class:`+report.Activity.emanation_baseline`
    %      - Emanation baseline
    %    * - :class:`+report.Activity.lowprob_anomaly`
    %      - Low probability anomaly
    %    * - :class:`+report.Activity.altered_anomaly`
    %      - Altered anomaly
    %    * - :class:`+report.Activity.mimic_anomaly`
    %      - Mimic anomaly
    %    * - :class:`+report.Activity.emanation_anomaly`
    %      - Emanation anomaly
    %    * - :class:`+report.Activity.lowprob_anomaly_snuggler`
    %      - Low probability anomaly (snuggler)
    %    * - :class:`+report.Activity.lowprob_anomaly_dsss`
    %      - Low probability anomaly (DSSS)
    %    * - :class:`+report.Activity.lowprob_anomaly_burst`
    %      - Low probability anomaly (burst)
    %    * - :class:`+report.Activity.lowprob_anomaly_fhss`
    %      - Low probability anomaly (FHSS)
    %
    enumeration
        overt_baseline
        overt_new
        emanation_baseline
        lowprob_anomaly
        altered_anomaly
        mimic_anomaly
        emanation_anomaly
        lowprob_anomaly_snuggler
        lowprob_anomaly_dsss
        lowprob_anomaly_burst
        lowprob_anomaly_fhss
    end
end