import paramiko
import re

def test_parse():
    raw = """SIP/OUT-HYM-00000d29!from-trunk!800950474115704!1!Down!AppDial!(Outgoing Line)!800950474115704!!!3!0!!1788700152.25906
SIP/OUT-HYM-00000c8f!macro-dialout-trunk!s!1!Up!AppDial!(Outgoing Line)!800950474115702!!!3!628!4a74fd2a-a39c-4307-88d6-67cbac88354e!1788699524.24606"""
    
    for line in raw.splitlines():
        parts = line.split("!")
        print(f"Total parts: {len(parts)}")
        for i, p in enumerate(parts):
            print(f"  {i}: {p}")

test_parse()
