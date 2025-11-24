'use client';

import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Upload, Camera, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

const PipelineUpload = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [showCamera, setShowCamera] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState<string>('');

  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setUploadProgress(10);
    setUploadStatus('Uploading image...');

    const formData = new FormData();
    formData.append('image', file);

    try {
      setUploadStatus('Submitting to API...');
      setUploadProgress(20);

      const response = await fetch('http://localhost:5000/api/pipeline/process', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!data.ok || !data.job_id) {
        throw new Error(data.message || 'Failed to start processing');
      }

      console.log('Job started:', data.job_id);
      setUploadProgress(30);
      setUploadStatus('Processing image...');

      const jobId = data.job_id;
      let attempts = 0;
      const maxAttempts = 60;

      const pollStatus = async (): Promise<boolean> => {
        try {
          const statusResponse = await fetch(`http://localhost:5000/api/pipeline/status/${jobId}`);
          const statusData = await statusResponse.json();

          if (statusData.status === 'completed') {
            setUploadProgress(100);
            setUploadStatus('Complete! Redirecting...');

            setTimeout(() => {
              window.location.href = `/dashboard`;
            }, 1500);

            return true;
          } else if (statusData.status === 'error') {
            throw new Error(statusData.message || 'Processing failed');
          } else {
            const progress = Math.min(90, 30 + (statusData.progress || 0) * 0.6);
            setUploadProgress(progress);
            setUploadStatus(statusData.message || 'Processing...');
            return false;
          }
        } catch (error) {
          console.error('Error polling status:', error);
          return false;
        }
      };

      while (attempts < maxAttempts) {
        const isComplete = await pollStatus();
        if (isComplete) break;

        await new Promise(resolve => setTimeout(resolve, 2000));
        attempts++;
      }

      if (attempts >= maxAttempts) {
        setUploadStatus('Processing is taking longer than expected...');
        setTimeout(() => {
          window.location.href = `/dashboard`;
        }, 2000);
      }

    } catch (error) {
      console.error('Upload failed:', error);
      setUploadStatus('Upload failed ❌');
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setUploadStatus('');
      }, 3000);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });
      setStream(mediaStream);
      setShowCamera(true);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (error) {
      console.error('Camera error:', error);
      alert('Could not access camera. Please check permissions.');
    }
  };

  const capturePhoto = () => {
    if (videoRef.current) {
      const canvas = document.createElement('canvas');
      canvas.width = videoRef.current.videoWidth;
      canvas.height = videoRef.current.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx?.drawImage(videoRef.current, 0, 0);

      canvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], 'camera-photo.jpg', { type: 'image/jpeg' });
          stopCamera();
          handleFileUpload(file);
        }
      }, 'image/jpeg');
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
      setShowCamera(false);
    }
  };

  if (showCamera) {
    return (
      <div className="fixed inset-0 bg-gradient-to-br from-[#0a1b2a] to-[#1e3a52] flex flex-col">
        <div className="flex items-center justify-between p-6 bg-black/20 backdrop-blur-sm">
          <button
            onClick={stopCamera}
            className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-md rounded-xl text-white hover:bg-white/20 transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Back</span>
          </button>
          <h1 className="text-xl font-bold text-white">Take Photo</h1>
          <div className="w-24" />
        </div>

        <div className="flex-1 flex items-center justify-center p-6">
          <div className="relative w-full max-w-4xl aspect-video">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              className="w-full h-full rounded-2xl object-cover shadow-2xl"
            />

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={capturePhoto}
              className="absolute bottom-8 left-1/2 transform -translate-x-1/2 w-20 h-20 bg-white rounded-full flex items-center justify-center shadow-2xl"
            >
              <div className="w-16 h-16 bg-gradient-to-br from-[#5BAAA7] to-[#1A6A6A] rounded-full flex items-center justify-center">
                <Camera className="w-8 h-8 text-white" />
              </div>
            </motion.button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-[#0a1b2a] to-[#1e3a52] flex flex-col">
      <div className="flex items-center justify-between p-6 bg-black/20 backdrop-blur-sm">
        <Link href="/dashboard">
          <button className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-md rounded-xl text-white hover:bg-white/20 transition-all">
            <ArrowLeft className="w-5 h-5" />
            <span>Dashboard</span>
          </button>
        </Link>
        <h1 className="text-2xl font-bold text-white">
          <span className="text-[#5BAAA7]">de</span>Cluttered<span className="text-[#5BAAA7]">.ai</span>
        </h1>
        <div className="w-32" />
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-6xl w-full">
          <div className="text-center mb-16">
            <h2 className="text-5xl font-bold text-white mb-4">Upload or Capture</h2>
            <p className="text-2xl text-gray-300">Choose how you want to add your image</p>
          </div>

          <div className="grid md:grid-cols-2 gap-12 max-w-5xl mx-auto">
            <motion.button
              whileHover={{ scale: 1.05, y: -10 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => fileInputRef.current?.click()}
              className="group relative bg-white/10 backdrop-blur-md border-2 border-white/30 rounded-3xl p-16 text-center hover:border-[#5BAAA7] hover:bg-white/15 transition-all duration-300 shadow-2xl hover:shadow-3xl"
            >
              <div className="flex flex-col items-center">
                <div className="w-32 h-32 mb-8 bg-gradient-to-br from-[#5BAAA7] to-[#1A6A6A] rounded-3xl flex items-center justify-center shadow-2xl group-hover:shadow-[#5BAAA7]/50 transition-all">
                  <Upload className="w-16 h-16 text-white" />
                </div>
                <h3 className="text-4xl font-bold text-white mb-4">Upload Image</h3>
                <p className="text-gray-300 text-xl">Choose from your device</p>
              </div>
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.05, y: -10 }}
              whileTap={{ scale: 0.98 }}
              onClick={startCamera}
              className="group relative bg-white/10 backdrop-blur-md border-2 border-white/30 rounded-3xl p-16 text-center hover:border-[#5BAAA7] hover:bg-white/15 transition-all duration-300 shadow-2xl hover:shadow-3xl"
            >
              <div className="flex flex-col items-center">
                <div className="w-32 h-32 mb-8 bg-gradient-to-br from-[#5BAAA7] to-[#1A6A6A] rounded-3xl flex items-center justify-center shadow-2xl group-hover:shadow-[#5BAAA7]/50 transition-all">
                  <Camera className="w-16 h-16 text-white" />
                </div>
                <h3 className="text-4xl font-bold text-white mb-4">Take Photo</h3>
                <p className="text-gray-300 text-xl">Use your camera</p>
              </div>
            </motion.button>
          </div>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        className="hidden"
      />

      {isUploading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50"
        >
          <div className="bg-white/10 backdrop-blur-md rounded-3xl p-12 max-w-md w-full mx-4 border-2 border-white/20">
            <div className="text-center mb-8">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-20 h-20 mx-auto mb-6 border-4 border-[#5BAAA7] border-t-transparent rounded-full"
              />
              <h3 className="text-2xl font-bold text-white mb-2">
                {uploadProgress === 100 ? 'Complete!' : 'Processing...'}
              </h3>
              <p className="text-gray-300 text-lg">{uploadStatus}</p>
            </div>

            <div className="w-full bg-white/20 rounded-full h-4 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${uploadProgress}%` }}
                transition={{ duration: 0.3 }}
                className="h-full bg-gradient-to-r from-[#5BAAA7] to-[#1A6A6A] rounded-full"
              />
            </div>
            <p className="text-center text-white mt-4 text-lg font-semibold">
              {uploadProgress}%
            </p>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default PipelineUpload;