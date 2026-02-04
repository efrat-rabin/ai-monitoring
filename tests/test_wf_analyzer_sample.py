# Temporary file for PR workflow test. Code without logging so analyzer suggests fixes.
# This file is created by tests/test_pr_workflow_apply_refresh.py and can be deleted after the test.

def process_item(item):
    result = item.upper()
    return result


def handle_request(req):
    try:
        logger.info('handling_request', {'request_data': req})
        data = req.get("data")
        return data
    except Exception as e:
        logger.error('request_handling_failed', {'error': str(e), 'error_type': type(e).__name__, 'request': req})
        raise


def batch_process(items):
    for i, x in enumerate(items):
        y = x.strip()
        if not y:
            return False
    return True
