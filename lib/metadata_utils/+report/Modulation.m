classdef Modulation < handle
    % This class is used to store the list of modulation types
    % 
    % .. list-table::
    %    :widths: 10 90
    %    :header-rows: 1
    %
    %    * - Signal
    %      - Description
    %    * - :class:`+report.Modulation.psk`
    %      - Phase Shift Keying
    %    * - :class:`+report.Modulation.bpsk`
    %      - Binary Phase Shift Keying
    %    * - :class:`+report.Modulation.qpsk`
    %      - Quadrature Phase Shift Keying
    %    * - :class:`+report.Modulation.psk8`
    %      - 8-Phase Shift Keying
    %    * - :class:`+report.Modulation.psk16`
    %      - 16-Phase Shift Keying
    %    * - :class:`+report.Modulation.psk32`
    %      - 32-Phase Shift Keying
    %    * - :class:`+report.Modulation.dbpsk`
    %      - Differential Binary Phase Shift Keying
    %    * - :class:`+report.Modulation.dqpsk`
    %      - Differential Quadrature Phase Shift Keying
    %    * - :class:`+report.Modulation.oqpsk`
    %      - Offset Quadrature Phase Shift Keying
    %    * - :class:`+report.Modulation.fm`
    %      - Frequency Modulation
    %    * - :class:`+report.Modulation.am`
    %      - Amplitude Modulation
    %    * - :class:`+report.Modulation.no_answer`
    %      - No answer
    %    * - :class:`+report.Modulation.unknown`
    %      - Unknown
    %    * - :class:`+report.Modulation.fsk2`
    %      - 2-Frequency Shift Keying
    %    * - :class:`+report.Modulation.fsk4`
    %      - 4-Frequency Shift Keying
    %    * - :class:`+report.Modulation.fsk8`
    %      - 8-Frequency Shift Keying
    %    * - :class:`+report.Modulation.fsk16`
    %      - 16-Frequency Shift Keying
    %    * - :class:`+report.Modulation.fsk32`
    %      - 32-Frequency Shift Keying
    %    * - :class:`+report.Modulation.fsk64`
    %      - 64-Frequency Shift Keying
    %    * - :class:`+report.Modulation.fsk128`
    %      - 128-Frequency Shift Keying
    %    * - :class:`+report.Modulation.cpfsk2`
    %      - 2-Continuous Phase Frequency Shift Keying
    %    * - :class:`+report.Modulation.cpfsk4`
    %      - 4-Continuous Phase Frequency Shift Keying
    %    * - :class:`+report.Modulation.cpfsk8`
    %      - 8-Continuous Phase Frequency Shift Keying
    %    * - :class:`+report.Modulation.cpfsk16`
    %      - 16-Continuous Phase Frequency Shift Keying
    %    * - :class:`+report.Modulation.cpfsk32`
    %      - 32-Continuous Phase Frequency Shift Keying
    %    * - :class:`+report.Modulation.cpfsk64`
    %      - 64-Continuous Phase Frequency Shift Keying
    %    * - :class:`+report.Modulation.qam8`
    %      - 8-Quadrature Amplitude Modulation
    %    * - :class:`+report.Modulation.qam16`
    %      - 16-Quadrature Amplitude Modulation
    %    * - :class:`+report.Modulation.qam32`
    %      - 32-Quadrature Amplitude Modulation
    %    * - :class:`+report.Modulation.qam64`
    %      - 64-Quadrature Amplitude Modulation
    %    * - :class:`+report.Modulation.qam128`
    %      - 128-Quadrature Amplitude Modulation
    %    * - :class:`+report.Modulation.qam256`
    %      - 256-Quadrature Amplitude Modulation
    %    * - :class:`+report.Modulation.qam1024`
    %      - 1024-Quadrature Amplitude Modulation
    %    * - :class:`+report.Modulation.gfsk`
    %      - Gaussian Frequency Shift Keying
    %    * - :class:`+report.Modulation.msk`
    %      - Minimum Shift Keying
    %    * - :class:`+report.Modulation.gmsk`
    %      - Gaussian Minimum Shift Keying
    %    * - :class:`+report.Modulation.cpfsk`
    %      - Continuous Phase Frequency Shift Keying
    %    * - :class:`+report.Modulation.ofdm`
    %      - Orthogonal Frequency Division Multiplexing
    %    * - :class:`+report.Modulation.css`
    %      - Chirp Spread Spectrum
    %    * - :class:`+report.Modulation.ook`
    %      - On-Off Keying
    %    * - :class:`+report.Modulation.ppm`
    %      - Pulse Position Modulation
    %    * - :class:`+report.Modulation.pwm`
    %      - Pulse Width Modulation
    %    * - :class:`+report.Modulation.ask4`
    %      - 4-Amplitude Shift Keying
    %    * - :class:`+report.Modulation.ask8`
    %      - 8-Amplitude Shift Keying
    %    * - :class:`+report.Modulation.ask16`
    %      - 16-Amplitude Shift Keying
    %    * - :class:`+report.Modulation.apsk16`
    %      - 16-Amplitude Phase Shift Keying
    %    * - :class:`+report.Modulation.apsk32`
    %      - 32-Amplitude Phase Shift Keying
    %    * - :class:`+report.Modulation.apsk64`
    %      - 64-Amplitude Phase Shift Keying
    %    * - :class:`+report.Modulation.pam`
    %      - Pulse Amplitude Modulation
    %    * - :class:`+report.Modulation.qam`
    %      - Quadrature Amplitude Modulation
    %    * - :class:`+report.Modulation.fh`
    %      - Frequency Hopping
    %    * - :class:`+report.Modulation.ssb`
    %      - Single Side Band


    enumeration
        psk
        bpsk
        qpsk
        psk8
        psk16
        psk32
        dbpsk
        dqpsk
        oqpsk
        fm
        am
        no_answer
        unknown
        fsk2
        fsk4
        fsk8
        fsk16
        fsk32
        fsk64
        fsk128

        cpfsk2
        cpfsk4
        cpfsk8
        cpfsk16
        cpfsk32
        cpfsk64

        qam8
        qam16
        qam32
        qam64
        qam128
        qam256
        qam1024
        
        gfsk
        msk
        gmsk
        cpfsk
        ofdm
        css
        ook
        ppm
        pwm
        ask4
        ask8
        ask16
        apsk16
        apsk32
        apsk64
        pam
        qam
        fh % freq hopping
        ssb
      
    end
end