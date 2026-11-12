app_name = "amc_pilot"
app_title = "AMCPilot"
app_publisher = "Cloudverce"
app_description = "AMC and service visit management for RO and appliance service businesses"
app_email = "nikunj7943@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "amc_pilot",
# 		"logo": "/assets/amc_pilot/logo.png",
# 		"title": "AMCPilot",
# 		"route": "/amc_pilot",
# 		"has_permission": "amc_pilot.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `amc_pilot/dock/amc_pilot/amc_pilot.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/amc_pilot/css/amc_pilot.css"
# app_include_js = "/assets/amc_pilot/js/amc_pilot.js"

# include js, css files in header of web template
# web_include_css = "/assets/amc_pilot/css/amc_pilot.css"
# web_include_js = "/assets/amc_pilot/js/amc_pilot.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "amc_pilot/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "amc_pilot/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "amc_pilot.utils.jinja_methods",
# 	"filters": "amc_pilot.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "amc_pilot.install.before_install"
# after_install = "amc_pilot.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "amc_pilot.uninstall.before_uninstall"
# after_uninstall = "amc_pilot.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "amc_pilot.utils.before_app_install"
# after_app_install = "amc_pilot.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "amc_pilot.utils.before_app_uninstall"
# after_app_uninstall = "amc_pilot.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "amc_pilot.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "amc_pilot.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "amc_pilot.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["amc_pilot.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"amc_pilot.tasks.all"
# 	],
# 	"daily": [
# 		"amc_pilot.tasks.daily"
# 	],
# 	"hourly": [
# 		"amc_pilot.tasks.hourly"
# 	],
# 	"weekly": [
# 		"amc_pilot.tasks.weekly"
# 	],
# 	"monthly": [
# 		"amc_pilot.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "amc_pilot.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "amc_pilot.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "amc_pilot.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "amc_pilot.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["amc_pilot.utils.before_request"]
# after_request = ["amc_pilot.utils.after_request"]

# Job Events
# ----------
# before_job = ["amc_pilot.utils.before_job"]
# after_job = ["amc_pilot.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"amc_pilot.auth.validate"
# ]

# on_social_login = "amc_pilot.auth.on_social_login"

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# Roles are created from fixtures/role.json on install and on every migrate.
# (Patches do not run on a fresh install, fixtures do.)
fixtures = [{"dt": "Role", "filters": [["name", "in", ["AMC Owner", "AMC Technician"]]]}]

# Apps screen icon (v16 desk). Route is the workspace page; see workspace/amcpilot.
add_to_apps_screen = [
	{
		"name": "amc_pilot",
		"title": "AMCPilot",
		"logo": "/assets/amc_pilot/images/logo.svg",
		"route": "/desk/amcpilot",
		"has_permission": "amc_pilot.amcpilot.services.access.has_app_permission",
		"sequence_id": 10,
	}
]

app_logo_url = "/assets/amc_pilot/images/logo.svg"

# Daily housekeeping: expire AMC Contracts whose term has passed.
scheduler_events = {
	"daily": [
		"amc_pilot.amcpilot.services.amc_contracts.expire_overdue_contracts",
	],
}
