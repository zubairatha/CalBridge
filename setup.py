from setuptools import setup

APP = ['helper_app.py']
OPTIONS = {
    'packages': [
        'fastapi', 'starlette', 'uvicorn', 'pydantic', 'anyio', 'sniffio', 'h11',
    ],
    'includes': [
        'EventKit', 'Foundation', 'AppKit',
    ],
    'plist': {
        'CFBundleName': 'CalBridge',
        'CFBundleIdentifier': 'dev.zubair.CalBridge',
        'NSCalendarsUsageDescription': 'CalBridge needs access to your calendars to read and create events.',
    },
    # uncomment during development for faster builds (alias mode keeps sources outside the bundle)
    # 'alias': True,
}

setup(app=APP, options={'py2app': OPTIONS}, setup_requires=['py2app'])
