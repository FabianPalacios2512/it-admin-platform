def run_on_dc(*args, **kwargs):
    print("Mock run_on_dc called with", args, kwargs)
    return {"status": "success", "message": "This is a mock response"}
