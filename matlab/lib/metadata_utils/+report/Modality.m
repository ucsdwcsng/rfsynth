classdef Modality < handle
    % This class is used to store the list of modality types
    % 
    % .. list-table::
    %    :widths: 10 90
    %    :header-rows: 1
    %
    %    * - Signal
    %      - Description
    %    * - :class:`+report.Modality.single_carrier`
    %      - Single carrier
    %    * - :class:`+report.Modality.multi_carrier`
    %      - Multi carrier
    %    * - :class:`+report.Modality.direct_sequence`
    %      - Direct sequence
    %    * - :class:`+report.Modality.frequency_agile`
    %      - Frequency agile
    %    * - :class:`+report.Modality.emanation`
    %      - Emanation
    %    * - :class:`+report.Modality.unknown`
    %      - Unknown
    %    * - :class:`+report.Modality.no_answer`
    %      - No answer

    enumeration
        single_carrier
        multi_carrier
        direct_sequence
        frequency_agile
        emanation
        unknown
        no_answer
    end
end