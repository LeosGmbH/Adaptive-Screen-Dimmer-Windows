"""
Process-based Overlay Manager
Manages separate overlay processes for each monitor
"""
import os
import sys
import subprocess
import tempfile
import time


class ProcessOverlayManager:
    """Manages overlay processes - one process per monitor"""
    
    def __init__(self, logger):
        self.logger = logger
        self.processes = {}  # monitor_id -> subprocess.Popen
        self.opacity_files = {}  # monitor_id -> temp file path
        self.current_opacity = {}
        self.target_opacity = {}
        self.temp_dir = tempfile.gettempdir()
        
        # Get path to overlay_process.py
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            self.script_dir = os.path.dirname(sys.executable)
        else:
            # Running as script - go up one level from HelperScripts
            self.script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.overlay_script = os.path.join(self.script_dir, "overlay_process.py")
    
    def create_overlay(self, monitor_id):
        """Start overlay process for monitor"""
        try:
            # Kill existing process if any
            if monitor_id in self.processes:
                self.destroy_overlay(monitor_id)
            
            # Create opacity file
            opacity_file = os.path.join(self.temp_dir, f"overlay_opacity_{monitor_id}.txt")
            self.opacity_files[monitor_id] = opacity_file
            
            # Initialize opacity to 0
            with open(opacity_file, 'w') as f:
                f.write("0")
            
            self.current_opacity[monitor_id] = 0
            self.target_opacity[monitor_id] = 0
            
            # Start process
            cmd = [sys.executable, self.overlay_script, str(monitor_id), opacity_file]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            self.processes[monitor_id] = process
            
            # Wait a bit for process to start
            time.sleep(0.2)
            
            # Check if process started successfully
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.logger.log(f"ERROR: Overlay process for monitor {monitor_id} failed to start")
                self.logger.log(f"stdout: {stdout.decode()}")
                self.logger.log(f"stderr: {stderr.decode()}")
                return False
            
            self.logger.log(f"Overlay process started for monitor {monitor_id}")
            return True
            
        except Exception as e:
            self.logger.log(f"ERROR creating overlay process for monitor {monitor_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def set_overlay_opacity(self, monitor_id, opacity, force_immediate=False):
        """Set overlay opacity by writing to file"""
        try:
            # Check if process is running
            if monitor_id not in self.processes:
                return False
            
            process = self.processes[monitor_id]
            if process.poll() is not None:
                # Process died
                self.logger.log(f"WARNING: Overlay process for monitor {monitor_id} died")
                return False
            
            opacity = max(0, min(255, int(opacity)))
            
            if force_immediate:
                self.current_opacity[monitor_id] = opacity
            else:
                # Smooth interpolation (calculated here, actual is done in process)
                current = self.current_opacity.get(monitor_id, 0)
                diff = opacity - current
                
                if abs(diff) > 1:
                    self.current_opacity[monitor_id] = current + (diff * 0.15)
                else:
                    self.current_opacity[monitor_id] = opacity
            
            # Write to file
            opacity_file = self.opacity_files.get(monitor_id)
            if opacity_file:
                with open(opacity_file, 'w') as f:
                    f.write(str(int(self.current_opacity[monitor_id])))
                return True
            
            return False
            
        except Exception as e:
            self.logger.log(f"ERROR setting opacity for monitor {monitor_id}: {e}")
            return False
    
    def destroy_overlay(self, monitor_id):
        """Kill overlay process"""
        try:
            if monitor_id in self.processes:
                process = self.processes[monitor_id]
                process.terminate()
                
                # Wait up to 1 second for clean exit
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    # Force kill if doesn't exit
                    process.kill()
                
                del self.processes[monitor_id]
                self.logger.log(f"Overlay process terminated for monitor {monitor_id}")
            
            # Clean up opacity file
            if monitor_id in self.opacity_files:
                opacity_file = self.opacity_files[monitor_id]
                try:
                    if os.path.exists(opacity_file):
                        os.remove(opacity_file)
                except:
                    pass
                del self.opacity_files[monitor_id]
            
            # Clean up opacity tracking
            self.current_opacity.pop(monitor_id, None)
            self.target_opacity.pop(monitor_id, None)
            
        except Exception as e:
            self.logger.log(f"ERROR destroying overlay for monitor {monitor_id}: {e}")
    
    def destroy_all_overlays(self):
        """Kill all overlay processes"""
        for monitor_id in list(self.processes.keys()):
            self.destroy_overlay(monitor_id)
    
    def is_overlay_running(self, monitor_id):
        """Check if overlay process is still running"""
        if monitor_id not in self.processes:
            return False
        
        process = self.processes[monitor_id]
        return process.poll() is None
