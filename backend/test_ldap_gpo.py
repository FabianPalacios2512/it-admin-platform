from app.services.ad_service import _get_admin_connection, _get_search_base, _paged_search
from ldap3 import SUBTREE

conn = _get_admin_connection()
search_base = "CN=Policies,CN=System," + _get_search_base()
search_filter = "(objectClass=groupPolicyContainer)"
attributes = ["displayName", "cn", "whenChanged", "flags", "gPCMachineExtensionNames", "gPCUserExtensionNames"]

entries = _paged_search(conn, search_base, search_filter, attributes)

for entry in entries:
    print(entry.entry_attributes_as_dict)
