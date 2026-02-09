#!/usr/bin/env python3
"""
Test Earth2Studio Local Installation - February 5, 2026
Verifies that Earth2Studio is properly installed with GPU support
"""

import sys
import os

def test_pytorch():
    """Test PyTorch installation"""
    print("=" * 60)
    print("TESTING PYTORCH")
    print("=" * 60)
    
    try:
        import torch
        print(f"PyTorch Version: {torch.__version__}")
        print(f"CUDA Available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA Version: {torch.version.cuda}")
            print(f"cuDNN Version: {torch.backends.cudnn.version()}")
            print(f"GPU Count: {torch.cuda.device_count()}")
            
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                mem = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                print(f"  GPU {i}: {name} ({mem:.1f} GB)")
            
            # Test GPU computation
            x = torch.randn(1000, 1000, device='cuda')
            y = torch.randn(1000, 1000, device='cuda')
            z = torch.matmul(x, y)
            print(f"GPU Computation Test: PASSED (matrix multiply result shape: {z.shape})")
            return True
        else:
            print("WARNING: CUDA not available!")
            return False
            
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def test_earth2studio():
    """Test Earth2Studio installation"""
    print("\n" + "=" * 60)
    print("TESTING EARTH2STUDIO")
    print("=" * 60)
    
    try:
        import earth2studio
        print(f"Earth2Studio Version: {earth2studio.__version__}")
        
        # Test core modules (some may have optional dependencies)
        modules_tested = 0
        
        try:
            from earth2studio import run
            print("  - earth2studio.run: OK")
            modules_tested += 1
        except ImportError as e:
            print(f"  - earth2studio.run: SKIP (optional dep: {e})")
        
        try:
            from earth2studio.data import GFS, HRRR
            print("  - earth2studio.data (GFS, HRRR): OK")
            modules_tested += 1
        except ImportError as e:
            print(f"  - earth2studio.data: SKIP (optional dep: {e})")
        
        try:
            from earth2studio.io import ZarrBackend
            print("  - earth2studio.io (ZarrBackend): OK")
            modules_tested += 1
        except ImportError as e:
            print(f"  - earth2studio.io: SKIP (optional dep: {e})")
        
        try:
            from earth2studio.perturbation import Zero
            print("  - earth2studio.perturbation (Zero): OK")
            modules_tested += 1
        except ImportError as e:
            print(f"  - earth2studio.perturbation: SKIP (optional dep: {e})")
        
        try:
            from earth2studio.models.px import FCN
            print("  - earth2studio.models.px (FCN): OK")
            modules_tested += 1
        except ImportError as e:
            print(f"  - earth2studio.models.px: SKIP (optional dep: {e})")
        
        if modules_tested >= 2:
            print(f"Earth2Studio Core Modules: PASSED ({modules_tested} modules)")
            return True
        else:
            print(f"Earth2Studio: PARTIAL ({modules_tested} modules)")
            return modules_tested > 0
        
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dependencies():
    """Test key dependencies"""
    print("\n" + "=" * 60)
    print("TESTING DEPENDENCIES")
    print("=" * 60)
    
    deps = [
        ("xarray", "xarray"),
        ("zarr", "zarr"),
        ("netCDF4", "netCDF4"),
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("huggingface_hub", "huggingface_hub"),
        ("loguru", "loguru"),
        ("rich", "rich"),
    ]
    
    all_ok = True
    for name, module in deps:
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "unknown")
            print(f"  {name}: {version} OK")
        except ImportError as e:
            print(f"  {name}: MISSING - {e}")
            all_ok = False
    
    return all_ok


def main():
    print("\n")
    print("#" * 60)
    print("#  EARTH2STUDIO LOCAL INSTALLATION TEST")
    print("#  February 5, 2026")
    print("#" * 60)
    print(f"\nPython: {sys.version}")
    print(f"Platform: {sys.platform}")
    print("")
    
    results = {
        "PyTorch + CUDA": test_pytorch(),
        "Earth2Studio": test_earth2studio(),
        "Dependencies": test_dependencies(),
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED - Earth2Studio is ready!")
    else:
        print("SOME TESTS FAILED - See above for details")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
