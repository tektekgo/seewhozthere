#!/usr/bin/env python3
"""
Minimal Hailo test script based on official reference implementation.
This tests the Hailo chip with the simplest possible code.
"""

import numpy as np
import hailo_platform as hpf
import cv2

def test_hailo_minimal():
    """Test Hailo with minimal code from reference implementation."""
    
    print("=" * 60)
    print("Minimal Hailo Test")
    print("=" * 60)
    
    model_path = "models/retinaface_mobilenet_v1.hef"
    
    print(f"\n1. Loading HEF file: {model_path}")
    hef = hpf.HEF(model_path)
    print("   ✅ HEF loaded")
    
    print("\n2. Creating VDevice")
    with hpf.VDevice() as target:
        print("   ✅ VDevice created")
        
        print("\n3. Configuring network")
        configure_params = hpf.ConfigureParams.create_from_hef(
            hef,
            interface=hpf.HailoStreamInterface.PCIe
        )
        network_group = target.configure(hef, configure_params)[0]
        print("   ✅ Network configured")
        
        print("\n4. Getting vstream info")
        network_group_params = network_group.create_params()
        input_vstream_info = hef.get_input_vstream_infos()[0]
        output_vstream_infos = hef.get_output_vstream_infos()
        
        input_shape = input_vstream_info.shape
        print(f"   Input shape: {input_shape}")
        print(f"   Input name: {input_vstream_info.name}")
        print(f"   Output count: {len(output_vstream_infos)}")
        
        print("\n5. Creating vstream parameters")
        input_vstreams_params = hpf.InputVStreamParams.make_from_network_group(
            network_group,
            quantized=False,
            format_type=hpf.FormatType.UINT8
        )
        output_vstreams_params = hpf.OutputVStreamParams.make_from_network_group(
            network_group,
            quantized=False,
            format_type=hpf.FormatType.UINT8
        )
        print("   ✅ VStream parameters created")
        
        print("\n6. Creating test input")
        # Create random test input matching model shape
        height, width, channels = input_shape
        test_input = np.random.randint(0, 255, input_shape, dtype=np.uint8)
        print(f"   Test input shape: {test_input.shape}")
        print(f"   Test input dtype: {test_input.dtype}")
        print(f"   Test input size: {test_input.nbytes} bytes")
        
        print("\n7. Activating network and running inference")
        with network_group.activate(network_group_params):
            print("   ✅ Network activated")
            
            with hpf.InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                print("   ✅ InferVStreams created")
                
                # Prepare input (add batch dimension)
                input_batch = np.expand_dims(test_input, axis=0)
                input_dict = {input_vstream_info.name: input_batch}
                
                print(f"\n8. Running inference")
                print(f"   Input batch shape: {input_batch.shape}")
                print(f"   Input batch dtype: {input_batch.dtype}")
                print(f"   Input batch size: {input_batch.nbytes} bytes")
                
                try:
                    results = infer_pipeline.infer(input_dict)
                    print("   ✅ Inference successful!")
                    
                    print("\n9. Output results:")
                    for vstream_info in output_vstream_infos:
                        output = results[vstream_info.name]
                        print(f"   {vstream_info.name}: shape={output.shape}, dtype={output.dtype}")
                    
                    print("\n" + "=" * 60)
                    print("✅ TEST PASSED - Hailo is working!")
                    print("=" * 60)
                    return True
                    
                except Exception as e:
                    print(f"\n❌ Inference failed: {e}")
                    print("\n" + "=" * 60)
                    print("❌ TEST FAILED")
                    print("=" * 60)
                    return False


def test_with_camera():
    """Test with actual camera frame."""
    
    print("\n" + "=" * 60)
    print("Testing with Camera Frame")
    print("=" * 60)
    
    # Connect to camera
    rtsp_url = "rtsp://rakshak:m@Hal0ka$iddhi@192.168.1.75:554/stream1"
    print(f"\nConnecting to camera...")
    
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("❌ Failed to connect to camera")
        return False
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("❌ Failed to read frame")
        return False
    
    print(f"✅ Got frame: {frame.shape}")
    
    # Now test Hailo with this frame
    model_path = "models/retinaface_mobilenet_v1.hef"
    
    hef = hpf.HEF(model_path)
    
    with hpf.VDevice() as target:
        configure_params = hpf.ConfigureParams.create_from_hef(
            hef,
            interface=hpf.HailoStreamInterface.PCIe
        )
        network_group = target.configure(hef, configure_params)[0]
        network_group_params = network_group.create_params()
        
        input_vstream_info = hef.get_input_vstream_infos()[0]
        output_vstream_infos = hef.get_output_vstream_infos()
        
        input_vstreams_params = hpf.InputVStreamParams.make_from_network_group(
            network_group,
            quantized=False,
            format_type=hpf.FormatType.UINT8
        )
        output_vstreams_params = hpf.OutputVStreamParams.make_from_network_group(
            network_group,
            quantized=False,
            format_type=hpf.FormatType.UINT8
        )
        
        # Preprocess frame
        input_shape = input_vstream_info.shape
        height, width = input_shape[0], input_shape[1]
        
        print(f"\nPreprocessing frame:")
        print(f"  Original: {frame.shape}")
        print(f"  Target: {input_shape}")
        
        resized = cv2.resize(frame, (width, height))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        print(f"  Preprocessed: {rgb.shape}, dtype={rgb.dtype}")
        
        with network_group.activate(network_group_params):
            with hpf.InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                
                input_batch = np.expand_dims(rgb, axis=0)
                input_dict = {input_vstream_info.name: input_batch}
                
                print(f"\nRunning inference on camera frame...")
                
                try:
                    results = infer_pipeline.infer(input_dict)
                    print("✅ Inference successful with camera frame!")
                    
                    print("\n" + "=" * 60)
                    print("✅ CAMERA TEST PASSED")
                    print("=" * 60)
                    return True
                    
                except Exception as e:
                    print(f"❌ Inference failed: {e}")
                    print("\n" + "=" * 60)
                    print("❌ CAMERA TEST FAILED")
                    print("=" * 60)
                    return False


if __name__ == "__main__":
    # Test 1: Minimal test with random data
    success1 = test_hailo_minimal()
    
    # Test 2: Test with actual camera frame
    if success1:
        success2 = test_with_camera()
    else:
        print("\nSkipping camera test due to minimal test failure")
        success2 = False
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print(f"  Minimal test: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"  Camera test:  {'✅ PASS' if success2 else '❌ FAIL'}")
    print("=" * 60)
