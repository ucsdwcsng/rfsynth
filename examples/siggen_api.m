%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% main_siggen.m
% An example of using the signal generation engine
%
% Author: Amy Hu, Raghav Subbaraman
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

rng(1);

%% High level Parameters for the VirtualSignalGenerator

% If this is set to false, only metadata is generated.
flagOutputIqSamples = true;

% Total time to generate data
tot_time = 0.02;

% Engine output data rates, bandwidth and center frequency
% Output rate of signals produced (Hz)
rxSampleRate_Hz = 122.88e6;
% Analog bandwidth is assumed to be = sample rate
bandwidth_Hz = 1*rxSampleRate_Hz;
% Center frequency of the output signals produced (Hz)
centerFreq_Hz = 2.45e9;

% Rx Location
rxLocation = [0 0 0];

% Create an Rx view point for the generator
rx = atomic.Rx('rx1', rxSampleRate_Hz, centerFreq_Hz, rxLocation);

%% Set up a Source in the testbed

% Required parameters
source1Name = 'WiFiRouter1'; % A name for the source
source1Origin = 'custom label';
source1Loc = [7.62 11.2 0]; % currently unused, but required.

% Optional parameters

% For more information, look at atomic.Source.applyChanneltoSignal
% HEURISTICNORM applies a heuristic tap-delay line channel which does not
% change the power of the signal.
% The default value for Channel is "IDENTITY" and is equivalent to having
% no channel.
source1Channel = "HEURISTICNORM";

% RF Imperfections:
% Carrier frequency offset in Hz. Defaults to zero
source1FreqOffset = 1234;

% This sets the gain and phase imbalance of the source for each signal
% associated with it. Expressed as [linear; radian], with a default value
% of [0;0] (no IQ imbalance). [gain_imbalance; phase_imbalance]
source1IQImbal = [0;0];

% Set the relative DC offset of the source for every signal. DC offset in
% baseband manifests itself as LO leakage or bleed-through in the final
% spectrum. Expressed as [linear; radian], with a default value of [0;0]
% (no LO leakage). [DC_relative_power; DC_phase]
% relative power is computed w.r.t to the signal power in dBm.
source1DCOffset =  [db2mag(-30);0];

% Create object with imperfection definition
imperfectionCfg = atomic.RFImperfections(source1FreqOffset,source1IQImbal,source1DCOffset);

% Declare source with parameters
source1 = atomic.Source(source1Name, source1Origin, rxSampleRate_Hz, source1Loc, source1Channel, imperfectionCfg);

%% Create a few more sources
source2Name = 'BLETag1';
source2Origin = 'custom label';
source2Loc = (2*rand(1,3)-1)*10;
source2FreqOffset = 1000*(2*rand-1);
imperfectionCfg = atomic.RFImperfections(source2FreqOffset);
source2 = atomic.Source(source2Name, source2Origin, rxSampleRate_Hz, source2Loc, "IDENTITY", imperfectionCfg);

source3Name = 'DSSSUser1';
source3Origin = 'custom label';
source3Loc = (2*rand(1,3)-1)*10;
source3FreqOffset = 1000*(2*rand-1);
imperfectionCfg = atomic.RFImperfections(source3FreqOffset);
source3 = atomic.Source(source3Name, source3Origin, rxSampleRate_Hz, source3Loc, "HEURISTICNORM", imperfectionCfg);

% Special source for thermal noise
sourceThermal = atomic.Source('Noise', 'custom label', rxSampleRate_Hz, [0 0 0]);
% This is a special source that will generate a noise signal to test
% outputs at various SNR. In the future, a receiver model will be used in
% the testbed, at which point the receiver will be adding the noise.

%% Create and add Signals to source1 (2 Channels of WiFi)

wlanCenterFreq_Hz = 2412e6; % Channel 1
transmissionPerSec = 100; % 100 transmissions in a second
trafficType = atomic.Traffic('periodic', 'transmissionPerSec', transmissionPerSec); % Initiate traffic type class as periodic
txPower_dbm = -74; % Power at the output of the engine

wlan_nonHT_80211g_c1 = atomic.WlanNonHT80211g( ...
    "trafficType", ...
    trafficType, ...
    "centerFreq_Hz",...
    wlanCenterFreq_Hz, ...
    "txPower_db",...
    txPower_dbm);

% Create a traffic type and manually supply required start-times (in
% seconds) that you require
wlanCenterFreq_Hz = 2437e6; % Channel 6
trafficType = atomic.Traffic('customArray','arrivalArray',[2 4 8 16]*1e-3);
txPower_dbm = -67;
wlan_nonHT_80211g_c6 = atomic.WlanNonHT80211g( ...
    "trafficType", ...
    trafficType, ...
    "centerFreq_Hz",...
    wlanCenterFreq_Hz, ...
    "txPower_db",...
    txPower_dbm);


% Add signals to source1
source1.addSignal(wlan_nonHT_80211g_c1);
source1.addSignal(wlan_nonHT_80211g_c6);

%% Create and add Signals to source2 (BLE Advertisement)
txPower_dbm = -79;
%
% Create BLE signal
bleCenterFreq_Hz = 2402e6; % First Adv Channel
message = randi([0 1],640,1); % A random message
transmissionPerSec = 100; % 100 transmissions in a second
trafficType = atomic.Traffic('periodic', 'transmissionPerSec', transmissionPerSec); % Initiate traffic type class as periodic

ble_adv_channel_2402 = atomic.Bluetooth( ...
    'trafficType',...
    trafficType, ...
    "centerFreq_Hz",...
    bleCenterFreq_Hz, ...
    "txPower_db",...
    txPower_dbm, ...
    "message",...
    message);

% Add signal to source2
source2.addSignal(ble_adv_channel_2402);

%% DSSS
txPower_dbm = -80;
ds3CenterFreq_Hz = 2460e6;
transmissionPerSec = 100;
trafficType = atomic.Traffic('periodic', 'transmissionPerSec', transmissionPerSec); % Initiate traffic type class as periodic
ds3SpreadFactor = 64; % Chip Rate
ds3DwellTime = 1e-3; % Length of ds3 transmission (seconds)
ds3Bandwidth_Hz = 35e6;

ds3 = atomic.Ds3( ...
    "trafficType",...
    trafficType, ... % Note that 'periodic' is convertible to atomic.Traffic('periodic')
    "centerFreq_Hz",...
    ds3CenterFreq_Hz, ...
    "bandwidth_Hz",...
    ds3Bandwidth_Hz, ...
    "txPower_db",...
    txPower_dbm, ...
    'chipsPerSymbol', ...
    ds3SpreadFactor, 'transmissionTotTime', ds3DwellTime);

source3.addSignal(ds3);

%% Thermal noise

% % Set temperature
thermalTemp_K = 290;
% % This constructor uses parameters from the top-level of the sig-gen since
% % noise is present everywhere
wb_thermal_noise_hdl = atomic.WidebandThermalWgn( "bandwidth_Hz",...
    bandwidth_Hz, ...
    "centerFreq_Hz",...
    centerFreq_Hz, ...
    "temperature_K",...
    thermalTemp_K);

sourceThermal.addSignal(wb_thermal_noise_hdl);


%% Instantiate engine, add sources and run it.
sigGen = VirtualSignalEngine();
sigGen.addRxObj(rx);
sigGen.addSource(source1);
sigGen.addSource(source2);
sigGen.addSource(source3);
sigGen.addSource(sourceThermal);

samplesIQ = sigGen.generateSamples(0, tot_time, flagOutputIqSamples);
metadataStr = sigGen.getMetadataJson;

%% Save engine outputs
sigGen.writeDataFiles(samplesIQ, metadataStr, "/tmp/", "testVirtualEngine");

%% Read things back
[readSamplesIQ, readMetadataStruct] = VirtualSignalEngine.readDataFiles("/tmp/", "testVirtualEngine");

% Access the bounding box for the first BLE signal
timeFreqBox = readMetadataStruct.sourceArray(2).signalArray.transmissionArray(1);
disp(timeFreqBox)

%% Plot results
p = PlotSignalHelper();
p.sampleFreq_Hz = rxSampleRate_Hz;
p.isUseTimeScale = true;
p.plotSignal(samplesIQ, sigGen);