"""Project configuration for MoleculeVerse.

Edit this file to change the institutional text or to fill in the developer
information shown on the About page. Nothing here is a secret; do NOT put
passwords or API keys in this file.
"""

APP_NAME = "MoleculeVerse"
APP_SUBTITLE = "Chemoinformatics Virtual Laboratory"

# Institutional information (provided project content; edit freely).
INSTITUTION = "SRM Institute of Science and Technology, Tiruchirappalli"
DEPARTMENT_LINE = (
    "Faculty of Engineering and Technology | School of Sciences | Division of Chemistry"
)

# About-page project details. Leave a value empty ("") if it is not known;
# the About page then shows "Not provided" instead of inventing anything.
DEVELOPER = {
    "Developer name": "",
    "Registration number": "",
    "Course": "",
    "Guide": "",
    "Academic year": "",
}

# The registration number is hidden on the About page unless this is True.
SHOW_REGISTRATION_ON_ABOUT = False

# Operational limits (also used for input validation).
MAX_COMPARE_MOLECULES = 8
MAX_MOLECULE_NAME_LENGTH = 60
