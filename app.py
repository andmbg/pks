
import os
from pks.dashboard import init_dashboard

# Get container name from environment or fallback
CONTAINER_NAME = os.environ.get("CONTAINER_NAME", "Unknown Container")

# Initialize Dash app directly
app = init_dashboard(route="/")

# Inject container name into the UI (if possible)
# try:
# 	import dash.html as html
# 	if hasattr(app, "layout") and hasattr(app.layout, "children"):
# 		app.layout.children.insert(0, html.Div(f"Container: {CONTAINER_NAME}", style={"color": "gray", "fontSize": "small"}))
# except Exception:
# 	pass

if __name__ == "__main__":
	port = int(os.environ.get("PORT", 8080))
	app.run(host="0.0.0.0", port=port, debug=False)
