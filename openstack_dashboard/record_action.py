"""Possible actions on an instance.

Actions should probably match a user intention at the API level.  Because they
can be user visible that should help to avoid confusion.  For that reason they
tend to maintain the casing sent to the API.

Maintaining a list of actions here should protect against inconsistencies when
they are used.
"""
DELETEINSTANCE = 'Delete Instance'
CREATEINSTANCE = 'Create Instance'
REGISTERLICENSE = 'Register License'
ADDAGENT = 'Add Agent'
DELETEAGENT = 'Delete Agent'
CREATEPORT = 'Create Port'
DELETEPORT = 'Delete Port'
DELETESUBNET = 'Delete Subnet'
CREATENETWORK = 'Create Network'
UPDATENETWORK = 'Update Network'
DELETENETWORK = 'Delete Network'
CHANGEPASSWORD = 'Change Password'
CREATETENANT = 'Create Tenant'
UPDATETENANT = 'Update Tenant'
DELETETENANT = 'Delete Tenant'
ADDINTERFACE = 'Add Interface'
SETGATEWAY = 'Set Gateway'
REMOVEINTERFACE = 'Remove Interface'
CREATEROUTER = 'Create Router'
UPDATEROUTER = 'Update Router'
DELETEROUTER = 'Delete Router'
CLEARGATEWAY = 'Clear Gateway'
USERSETTINGS = 'User Settings'
CREATEUSER = 'Create User'
UPDATEUSER = 'Update User'
TOGGLEUSER = 'Toggle User'
DELETEUSER = 'Delete User'
UPDATEPORT = 'Update Port'
UPDATESUBNET = 'Update Subnet'
CREATESUBNET = 'Create Subnet'
