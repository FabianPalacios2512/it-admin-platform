import win32evtlog
import win32evtlogutil
import winerror

server = "192.168.1.59"
logtype = "Microsoft-Windows-PrintService/Operational"

try:
    print(f"Trying to open Event Log {logtype} on {server}...")
    hand = win32evtlog.EvtQuery(server, win32evtlog.EvtQueryChannelPath, logtype, "*[System/EventID=307]")
    
    events = win32evtlog.EvtNext(hand, 10)
    print(f"Got {len(events)} events.")
except Exception as e:
    print(f"Error: {e}")
