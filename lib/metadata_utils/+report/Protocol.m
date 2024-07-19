classdef Protocol < handle
    % This class is used to store the list of protocols types
    % 
    % .. list-table::
    %    :widths: 10 90
    %    :header-rows: 1
    %
    %    * - Signal
    %      - Description
    %    * - :class:`+report.Protocol.wlan_wwan`
    %      - WLAN/WWAN
    %    * - :class:`+report.Protocol.wpan`
    %      - WPAN
    %    * - :class:`+report.Protocol.ics_scada`
    %      - ICS/SCADA
    %    * - :class:`+report.Protocol.cordless_telephony`
    %      - Cordless Telephony
    %    * - :class:`+report.Protocol.us_tv_bcast_svc`
    %      - US TV Broadcast Service
    %    * - :class:`+report.Protocol.us_radio_bcast_svc`
    %      - US Radio Broadcast Service
    %    * - :class:`+report.Protocol.cellular`
    %      - Cellular
    %    * - :class:`+report.Protocol.pmr_pamr_tmr_smr_lmr`
    %      - PMR/PAMR/TMR/SMR/LMR
    %    * - :class:`+report.Protocol.unknown`
    %      - Unknown
    %    * - :class:`+report.Protocol.no_answer`
    %      - No Answer
    
    enumeration
        wlan_wwan
        wpan
        ics_scada
        cordless_telephony
        us_tv_bcast_svc
        us_radio_bcast_svc
        cellular
        pmr_pamr_tmr_smr_lmr
        unknown
        no_answer
    end
end
