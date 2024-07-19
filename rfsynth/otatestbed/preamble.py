import numpy as np
import scipy.signal as signal
from fractions import Fraction
import matplotlib.pyplot as plt
from numpy.matlib import repmat

class Preamble:
    """This class is used to add and remove preambles from a sequence of samples"""
    sps = 2 # samples per symbol in all preambles
    # pn_sym_len = 1024 # symbol length of all preambles
    pn_mod_order = 2 # should be two to minimize symbol error probability
    # pn_len = pn_sym_len*sps

    def __init__(self, preamble_on_time_ms=100, seed=1234, fs=1, tx_rx_id=None):
        self.fs = fs
        self.seed = seed
        self.eps = 1e-28 #np.finfo(np.float64).eps, avoid divide by zero and log of zero errors
        self.tx_rx_id = tx_rx_id
        self.start_idx = None
        self.stop_idx = None
        self.sliced_seq = None 
        self.start_time = None    
        self.stop_time =  None 
        self.pn_sym_len = np.ceil(preamble_on_time_ms*1e-3*fs/Preamble.sps).astype(int)

    def insert(self, in_seq=np.array([1,2,3]), shape='square'):
        self.orig_seq = in_seq
        self.orig_seq_len = len(in_seq)
        pn_seq = self._get_pn_seq(shape)
        self.padded_seq = np.concatenate((pn_seq,in_seq))
        return self.padded_seq

    def remove(self, in_seq=np.array([1,2,3]), shape='square'):
        self.rx_seq = in_seq
        self._pn_seq = self._get_pn_seq(shape)
        # xcorr = np.correlate(in_seq, pn_seq,mode='valid')/len(pn_seq) # does not use fft based method
        self._xcorr = signal.correlate(in_seq, self._pn_seq, mode='valid')/len(self._pn_seq)
        self._noise_pow_est = self._get_noise_pow_est(np.abs(self._xcorr))
        self._threshold = 200*self._noise_pow_est # should be a multiple of the estimated noise floor 460
        peak_indices = np.argwhere(np.abs(self._xcorr) > self._threshold) # there can be many samples above the threshold
        if len(peak_indices) > 0:
            self._max_peak_idx = peak_indices[np.argmax(np.abs(self._xcorr[peak_indices]))] # now find the max of all samples above the threshold            
        else:
            self._max_peak_idx = []
        if len(self._max_peak_idx) != 1:
            # warnings.warn(f'\n\n{len(self._max_peak_idx)} preamble peaks found! There is nothing to do.') 
            print(f'{len(self._max_peak_idx)} preamble peaks found for Tx' \
                f'{self.tx_rx_id[0]}:{self.tx_rx_id[1]}-Rx{self.tx_rx_id[2]}:{self.tx_rx_id[3]}!')                          
            return None
        else:
            self.start_idx = self._max_peak_idx[0]+len(self._pn_seq)
            self.stop_idx = self.start_idx + self.orig_seq_len
            self.sliced_seq = in_seq[self.start_idx:self.stop_idx]  
            self.start_time = self.start_idx/self.fs     
            self.stop_time =  self.stop_idx/self.fs    
            return self.sliced_seq

    def plot_debug_xcorr(self, meta=None):
        # debug plots to see correlation peak
        plt.subplot(311)
        plt.plot(np.abs(self._xcorr))        
        plt.plot([0, len(self._xcorr)],[self._threshold, self._threshold], 'k--')
        plt.plot([0, len(self._xcorr)],[self._noise_pow_est, self._noise_pow_est], 'b--')
        plt.plot(self._max_peak_idx, np.abs(self._xcorr[self._max_peak_idx]),'ko')
        plt.xlabel('Sample Delay'); plt.ylabel('|xcorr|');
        if meta is None: 
            plt.title('Cross-correlation Output')
        else:     
            tx_num = meta[0]; tx_ch_num = meta[1]; rx_num = meta[2]; rx_ch_num = meta[3]
            plt.title(f'Cross-correlation Output Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.subplot(312)        
        plt.plot(np.real(self.rx_seq))        
        plt.plot([self.start_idx, self.start_idx], plt.gca().get_ylim(), 'k--')
        plt.plot([self.stop_idx, self.stop_idx], plt.gca().get_ylim(), 'k--')
        plt.xlabel('Sample Number'); plt.ylabel('Real Amplitude'); 
        if meta is None:
            plt.title('Signal with Preamble and Delay')
        else:
            plt.title(f'Signal with Preamble and Delay Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.subplot(313)
        plt.plot(np.real(self.sliced_seq))
        plt.xlabel('Sample Number'); plt.ylabel('Real Amplitude');
        if meta is None:
            plt.title('Sliced Output')
        else:
            plt.title(f'Sliced Output Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.tight_layout()

    def plot_debug_spectrograms(self, meta=None):        
        f_orig,t_orig,Sxx_orig = signal.spectrogram(self.orig_seq+self.eps, fs=self.fs, window=('hamming'), nperseg=256, noverlap=128, nfft=256, \
                detrend=False, return_onesided=False, scaling='density', axis=-1, mode='complex')
        f_in,t_in,Sxx_rx = signal.spectrogram(self.rx_seq, fs=self.fs, window=('hamming'), nperseg=256, noverlap=128, nfft=256, \
                detrend=False, return_onesided=False, scaling='density', axis=-1, mode='complex')
        if self.sliced_seq is not None:
            f_out,t_out,Sxx_sliced = signal.spectrogram(self.sliced_seq, fs=self.fs, window=('hamming'), nperseg=256, noverlap=128, nfft=256, \
                detrend=False, return_onesided=False, scaling='density', axis=-1, mode='complex')
        # clo_orig, chi_orig = self._get_spectro_color_bounds(Sxx_orig)
        clo_rx, chi_rx = self._get_spectro_color_bounds(Sxx_rx)
        # clo_sliced, chi_sliced = self._get_spectro_color_bounds(Sxx_sliced)
        plt.figure()
        plt.subplot(131)
        plt.pcolormesh(np.fft.fftshift(f_orig)*1e-6, t_orig*1e3, np.transpose(10*np.log10(1/256*np.abs(np.fft.fftshift(Sxx_orig,axes=0))**2+self.eps)), cmap='jet', vmin=clo_rx, vmax=chi_rx)  
        plt.xlabel('Frequency (MHz)'); plt.ylabel('Time (ms)'); 
        if meta is None: 
            plt.title('Input')
        else:     
            tx_num = meta[0]; tx_ch_num = meta[1]; rx_num = meta[2]; rx_ch_num = meta[3]
            plt.title(f'Input Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.subplot(132)
        plt.pcolormesh(np.fft.fftshift(f_in)*1e-6, t_in*1e3, np.transpose(10*np.log10(1/256*np.abs(np.fft.fftshift(Sxx_rx,axes=0))**2)), cmap='jet', vmin=clo_rx, vmax=chi_rx)  
        plt.xlabel('Frequency (MHz)'); plt.ylabel('Time (ms)'); 
        if meta is None: 
            plt.title('Received')
        else:
            plt.title(f'Received Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        if self.sliced_seq is not None:
            plt.subplot(133)
            plt.pcolormesh(np.fft.fftshift(f_out)*1e-6, t_out*1e3, np.transpose(10*np.log10(1/256*np.abs(np.fft.fftshift(Sxx_sliced,axes=0))**2)), cmap='jet', vmin=clo_rx, vmax=chi_rx)
            plt.colorbar() 
            plt.xlabel('Frequency (MHz)'); plt.ylabel('Time (ms)'); 
            if meta is None: 
                plt.title('Sliced')
            else:
                plt.title(f'Sliced Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')       

    def plot_debug_tx_time(self, meta=None):
        ## plot original sequence and preamble added sequence        
        plt.figure()
        plt.subplot(221)
        plt.plot(np.arange(len(self.orig_seq))*1/self.fs*1e3, np.real(self.orig_seq),'b-')
        plt.xlabel('Time (ms)'); plt.ylabel('Amplitude'); 
        if meta is None:
            plt.title('Transmitter Real Original Signal')
        else:
            tx_num = meta[0]; tx_ch_num = meta[1]; rx_num = meta[2]; rx_ch_num = meta[3]
            plt.title(f'Transmitter Real Original Signal Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.subplot(222)
        plt.plot(np.arange(len(self.orig_seq))*1/self.fs*1e3, np.imag(self.orig_seq),'r-')
        plt.xlabel('Time (ms)'); plt.ylabel('Amplitude'); 
        if meta is None:
            plt.title('Transmitter Imaginary Original Signal')
        else:
             plt.title(f'Transmitter Imaginary Original Signal Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.subplot(223)
        plt.plot(np.arange(len(self.padded_seq))*1/self.fs*1e3, np.real(self.padded_seq),'b-')
        plt.xlabel('Time (ms)'); plt.ylabel('Amplitude'); 
        if meta is None:
            plt.title('Transmitter Real Preamble Added Signal')
        else:
            plt.title(f'Transmitter Real Preamble Added Signal Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.subplot(224)
        plt.plot(np.arange(len(self.padded_seq))*1/self.fs*1e3, np.real(self.padded_seq),'b-')
        plt.xlabel('Time (ms)'); plt.ylabel('Amplitude'); 
        if meta is None:
            plt.title('Transmitter Imaginary Preamble Added Signal')
        else:
            plt.title(f'Transmitter Imaginary Preamble Added Signal Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.tight_layout()    

    def plot_debug_rx_time(self, meta=None):  
        ## plot received sequence and compare sliced to original sequence
        # scale sequences so the max values coincide to help visually compare
        rx_seq = self.rx_seq/np.max(np.abs(self.rx_seq))
        orig_seq = self.orig_seq/np.max(np.abs(self.orig_seq))
        if self.sliced_seq is not None:
            sliced_seq = self.sliced_seq/np.max(np.abs(self.sliced_seq))

        plt.figure()
        plt.subplot(221)
        plt.plot(np.arange(len(rx_seq))*1/self.fs*1e3, np.real(rx_seq),'b-')
        plt.xlabel('Time (ms)'); plt.ylabel('Amplitude'); 
        if meta is None:
            plt.title('Receiver Real Signal')
        else:
            tx_num = meta[0]; tx_ch_num = meta[1]; rx_num = meta[2]; rx_ch_num = meta[3]
            plt.title(f'Receiver Real Signal Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.subplot(222)
        plt.plot(np.arange(len(rx_seq))*1/self.fs*1e3, np.imag(rx_seq),'r-')
        plt.xlabel('Time (ms)'); plt.ylabel('Amplitude'); 
        if meta is None:
            plt.title('Imaginary Received Signal')
        else:
            plt.title(f'Imaginary Received Signal Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.subplot(223)
        plt.plot(np.arange(len(orig_seq))*1/self.fs*1e3, np.real(orig_seq),'b-', linewidth=1)
        if self.sliced_seq is not None:
            plt.plot(np.arange(len(sliced_seq))*1/self.fs*1e3, np.real(sliced_seq),'r.')
        plt.xlabel('Time (ms)'); plt.ylabel('Amplitude'); 
        if meta is None:
            plt.title('Real Part Compare Tx/Rx')
        else:
            plt.title(f'Real Part Compare Tx/Rx Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.subplot(224)
        plt.plot(np.arange(len(orig_seq))*1/self.fs*1e3, np.imag(orig_seq),'b-', linewidth=1)
        if self.sliced_seq is not None:
            plt.plot(np.arange(len(sliced_seq))*1/self.fs*1e3, np.imag(sliced_seq),'r.')
        plt.xlabel('Time (ms)'); plt.ylabel('Amplitude'); 
        if meta is None:
            plt.title('Imaginary Part Compare Tx/Rx')
        else:
            plt.title(f'Imaginary Part Compare Tx/Rx Tx{tx_num}:{tx_ch_num}-Rx{rx_num}:{rx_ch_num}')
        plt.tight_layout()

    def _get_spectro_color_bounds(self, Sxx):
        specv = np.ravel(10*np.log10(1/256*np.abs(Sxx)**2+self.eps))
        # specv = 10*np.log10(np.ravel(Sxx))
        num_min_vals = np.round(.1*len(specv)).astype(int)
        mink_vals = specv[np.argpartition(specv,num_min_vals)[:num_min_vals]]
        clo = np.average(mink_vals)+10; 
        chi = np.max(specv)-10
        return clo, chi

    def _get_pn_seq(self, shape):
        np.random.seed(self.seed)
        if shape.casefold() == 'rrc':        
            pass
        else:
            pn_symbols = 2*np.random.randint(0,Preamble.pn_mod_order,size=self.pn_sym_len)-1 + \
                1j*(2*np.random.randint(0,Preamble.pn_mod_order,size=self.pn_sym_len)-1)
            pn_seq = np.matlib.repmat(pn_symbols,Preamble.sps,1).flatten('F')

        return pn_seq

    def _get_noise_pow_est(self, in_seq):
        # _,_,psd = signal.spectrogram(in_seq, fs=self.fs, window=('hamming'), nperseg=256, noverlap=128, nfft=256, \
        #     detrend=False, return_onesided=False, scaling='density', axis=-1, mode='psd')
        # plt.pcolormesh(fft.fftshift(f)*1e-6, t*1e3, np.transpose(np.abs(fft.fftshift(Sxx,axes=0))), cmap='jet')  
        # plt.show()  
        # b = Sxx.reshape(-1,10,256)
        # c = np.mean(b,axis=1)
        k = np.round(0.001*len(in_seq)).astype(int) # the number of minimum samples to use for noise floor estimate
        # Sxx_mink = np.average(Sxx[np.argpartition(np.ravel(Sxx),k)[:k]])
        # Sxx_vec = np.ravel(psd)
        # pow_est = np.average(Sxx_vec[np.argpartition(Sxx_vec,k)[:k]])
        bias_correction = 20*3.1 # empirically found
        return bias_correction*np.average(in_seq[np.argpartition(in_seq,k)[:k]])

if __name__ == "__main__":  
    fs = 10e6 # sample rate
    preamble_on = 40 # preamble on-time (ms)
    Preamble.sps = 2
    Preamble.pn_sym_len = np.ceil(preamble_on*1e-3*fs/Preamble.sps).astype(int)
    preamble1_seed = 12000
    preamble = Preamble(preamble1_seed, fs)

    # preamble.unit_test()
