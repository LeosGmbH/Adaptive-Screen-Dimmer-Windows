"""
Adaptive Screen Dimmer - Main Entry Point

A tool that automatically dims bright screens to reduce eye strain.
"""
import time
import sys
import ctypes
from HelperScripts.gui import DimmerGUI


def main():
    """Main entry point for the application"""
    print("🔍 DEBUG: main() started")
    
    # Set DPI awareness
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
    
    # Check admin rights
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            print("⚠️  WARNUNG: Programm läuft nicht als Administrator")
            print("   Falls Probleme auftreten, mit Rechtsklick -> 'Als Administrator ausführen'\n")
    except:
        pass
    
    # Create and run GUI
    print("🔍 DEBUG: Creating DimmerGUI...")
    try:
        gui = DimmerGUI()
        print("🔍 DEBUG: DimmerGUI created successfully")
        print("🔍 DEBUG: Starting mainloop...")
        gui.root.mainloop()
        print("🔍 DEBUG: mainloop ended")
    except Exception as e:
        print(f"❌ ERROR in GUI creation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        time.sleep(3)
        sys.exit(1)
