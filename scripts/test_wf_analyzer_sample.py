# Temporary file for PR workflow test. Code without logging so analyzer suggests fixes.
# This file is created by scripts/test_pr_workflow_apply_refresh.py and can be deleted after the test.

def process_item(item):
    result = item.upper()
    return result


def handle_request(req):
    try:
        logger.info('handling_request', {'request_keys': list(req.keys()) if hasattr(req, 'keys') else None})
        data = req.get("data")
        return data
    except Exception as e:
        logger.error('request_failed', {'error': str(e), 'request_keys': list(req.keys()) if hasattr(req, 'keys') else None})
        raise


def batch_process(items):
    for i, x in enumerate(items):
        y = x.strip()
        if not y:
            return False
    return True
