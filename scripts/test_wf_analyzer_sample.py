# Temporary file for PR workflow test. Code without logging so analyzer suggests fixes.
# This file is created by scripts/test_pr_workflow_apply_refresh.py and can be deleted after the test.

def process_item(item):
    logger.info('processing_item', {'item': item})
    result = item.upper()
    return result


def handle_request(req):
    try:
        data = req.get("data")
        return data
    except Exception:
        raise


def batch_process(items):
    for i, x in enumerate(items):
        y = x.strip()
        if not y:
            return False
    return True
