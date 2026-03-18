"""Script to add e-commerce router to main.py"""

import re

# Read the main.py file
with open("backend/main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find where to insert (after litellm.drop_params = True)
insert_point = content.find("litellm.drop_params = True")
if insert_point == -1:
    print("Could not find insertion point")
    exit(1)

# Add the e-commerce router import
router_import = """
# Import specialized e-commerce routers
try:
    from ecommerce_endpoints import router as ecommerce_router
    print("✓ E-commerce router imported successfully")
except Exception as e:
    print(f"⚠ Could not import e-commerce router: {e}")
    ecommerce_router = None
"""

# Insert after litellm.drop_params = True
content = (
    content[: insert_point + len("litellm.drop_params = True")]
    + router_import
    + content[insert_point + len("litellm.drop_params = True") :]
)

# Find where to register the router (find @app.event("lifespan"))
# We'll add it before the lifespan decorator
lifespan_pattern = r"@asynccontextmanager\ndef lifespan\("
match = re.search(lifespan_pattern, content)
if match:
    # Add router registration after lifespan decorator
    router_registration = """

# Register e-commerce routers if available
if ecommerce_router:
    app.include_router(ecommerce_router, prefix="/crawl", tags=["E-commerce Crawlers"])
    print("✓ E-commerce routers registered successfully")

"""
    # Find the first @app decorator after imports
    insert_point = content.find("@app", match.start())
    if insert_point != -1:
        content = content[:insert_point] + router_registration + content[insert_point:]

# Write back
with open("backend/main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ Successfully added e-commerce router to main.py")
