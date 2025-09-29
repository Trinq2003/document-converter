#!/usr/bin/env python3
"""
Test script for retry mechanism in watermark batch processing
"""

import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Mock the watermark functionality to simulate failures
class MockWatermarkProcessor:
    def __init__(self, fail_patterns=None):
        self.fail_patterns = fail_patterns or []

    def process_file(self, input_path, output_path):
        """Mock processing that can fail based on patterns"""
        filename = os.path.basename(input_path)

        # Use a global counter for attempts (simplified for multiprocessing)
        attempt = get_attempt_count(filename) + 1
        set_attempt_count(filename, attempt)

        # Check if this file should fail on this attempt
        for pattern in self.fail_patterns:
            if pattern['filename'] == filename:
                if attempt <= pattern.get('fail_until_attempt', 1):
                    raise Exception(f"Simulated failure for {filename} on attempt {attempt}")

        # Success - copy file
        shutil.copy2(input_path, output_path)
        return True

# Global counters for multiprocessing compatibility
_attempt_counts = {}

def get_attempt_count(filename):
    return _attempt_counts.get(filename, 0)

def set_attempt_count(filename, count):
    _attempt_counts[filename] = count

# Global mock processor instance for multiprocessing compatibility
_global_mock_processor = None

def mock_process_single_file_wrapper(args):
    """Module-level mock function that can be pickled for multiprocessing"""
    global _global_mock_processor
    input_path, output_path, method = args
    try:
        _global_mock_processor.process_file(input_path, output_path)
        return input_path, True, ""
    except Exception as e:
        return input_path, False, str(e)

def create_test_files(base_dir, count=5):
    """Create test DOCX files"""
    test_files = []
    for i in range(count):
        filename = f"test_{i}.docx"
        filepath = os.path.join(base_dir, filename)

        # Create a minimal DOCX-like file (just for testing)
        with open(filepath, 'w') as f:
            f.write("Mock DOCX content")

        test_files.append(filepath)

    return test_files

def test_retry_mechanism():
    """Test the retry mechanism with simulated failures"""
    print("Testing Retry Mechanism")
    print("=" * 50)

    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        input_dir = os.path.join(temp_dir, "input")
        output_dir = os.path.join(temp_dir, "output")

        os.makedirs(input_dir)
        os.makedirs(output_dir)

        # Create test files
        test_files = create_test_files(input_dir, 5)
        print(f"Created {len(test_files)} test files")

        # Define failure patterns
        # - test_0.docx: fails twice, succeeds on third attempt
        # - test_1.docx: fails once, succeeds on second attempt
        # - test_2.docx: always fails
        # - test_3.docx: succeeds immediately
        # - test_4.docx: succeeds immediately

        fail_patterns = [
            {'filename': 'test_0.docx', 'fail_until_attempt': 2},
            {'filename': 'test_1.docx', 'fail_until_attempt': 1},
            {'filename': 'test_2.docx', 'fail_until_attempt': 10},  # Always fail
        ]

        # Import the batch processing function
        from app.watermark import add_watermarks_batch

        # Mock the process_single_file function to use our mock processor
        import app.watermark
        original_process = app.watermark.process_single_file

        mock_processor = MockWatermarkProcessor(fail_patterns)

        # Set global mock processor for multiprocessing compatibility
        global _global_mock_processor
        _global_mock_processor = mock_processor

        # Replace the function temporarily with a module-level function
        app.watermark.process_single_file = mock_process_single_file_wrapper

        try:
            # Prepare file pairs
            file_pairs = []
            for test_file in test_files:
                filename = os.path.basename(test_file)
                output_file = os.path.join(output_dir, filename)
                file_pairs.append((test_file, output_file))

            # Run batch processing with retry (max 3 retries)
            print("\nRunning batch processing with retry mechanism...")
            results = add_watermarks_batch(file_pairs, max_workers=2, max_retries=3)

            # Analyze results
            successful = [r for r in results if r[1]]
            failed = [r for r in results if not r[1]]

            print(f"\nTest Results:")
            print(f"Successful: {len(successful)}")
            print(f"Failed: {len(failed)}")

            print("\nDetailed Results:")
            for input_path, success, error_msg in results:
                status = "SUCCESS" if success else "FAILED"
                filename = os.path.basename(input_path)
                print(f"  {status}: {filename} - {error_msg or 'OK'}")

            # Verify expected behavior
            expected_successful = ['test_0.docx', 'test_1.docx', 'test_3.docx', 'test_4.docx']
            expected_failed = ['test_2.docx']

            actual_successful = [os.path.basename(r[0]) for r in successful]
            actual_failed = [os.path.basename(r[0]) for r in failed]

            if set(actual_successful) == set(expected_successful) and set(actual_failed) == set(expected_failed):
                print("\nRetry mechanism test PASSED!")
                return True
            else:
                print("\nRetry mechanism test FAILED!")
                print(f"Expected successful: {expected_successful}")
                print(f"Actual successful: {actual_successful}")
                print(f"Expected failed: {expected_failed}")
                print(f"Actual failed: {actual_failed}")
                return False

        finally:
            # Restore original function
            app.watermark.process_single_file = original_process

if __name__ == "__main__":
    success = test_retry_mechanism()
    print("\n" + "="*50)
    if success:
        print("OVERALL TEST RESULT: PASSED")
    else:
        print("OVERALL TEST RESULT: FAILED")
    sys.exit(0 if success else 1)
