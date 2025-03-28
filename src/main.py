#!/usr/bin/env python3
import sys
import logging
import argparse

# Ensure the src directory is in the Python path
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.app import ReadAloudApp

def setup_logging(verbose=False):
    """Set up logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def parse_args(args=None):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Linux Read Aloud application')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    # Parse only our arguments and leave the rest for the GTK application
    if args is None:
        args = sys.argv[1:]
    
    # Extract the arguments we care about
    our_args = []
    gtk_args = []
    
    i = 0
    while i < len(args):
        if args[i] == '--verbose' or args[i] == '-v':
            our_args.append('--verbose')
        else:
            gtk_args.append(args[i])
        i += 1
    
    parsed_args = parser.parse_args(our_args)
    
    # Replace sys.argv with only GTK arguments
    sys.argv = [sys.argv[0]] + gtk_args
    
    return parsed_args

def main():
    """Main entry point"""
    # Parse args before GTK tries to
    args = parse_args(sys.argv[1:])
    setup_logging(args.verbose)
    
    logging.info("Starting Read Aloud application")
    
    app = ReadAloudApp()
    logging.debug("Application instance created")
    result = app.run(sys.argv)
    logging.debug("Application exited with code %d", result)
    return result

if __name__ == "__main__":
    sys.exit(main()) 