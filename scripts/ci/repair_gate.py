"""Pure policy for a future trusted coordinator; does not invoke Codex or write git."""
AUTO_REVIEW_MAX_ITERATIONS = 3


def decide(status, iteration, human_gate=False):
    if status not in {'PASS', 'FAIL'} or type(iteration) is not int or not 0 <= iteration <= 3:
        return {'status': 'BLOCKED', 'next_action': 'HUMAN_REVIEW_REQUIRED', 'dispatch': False}
    if human_gate:
        return {'status': status, 'next_action': 'HUMAN_REVIEW_REQUIRED', 'dispatch': False}
    if status == 'PASS':
        return {'status': 'PASS', 'next_action': 'READY_FOR_HUMAN_REVIEW', 'dispatch': False}
    if iteration >= AUTO_REVIEW_MAX_ITERATIONS:
        return {'status': 'BLOCKED', 'next_action': 'HUMAN_REVIEW_REQUIRED', 'dispatch': False}
    return {'status': 'FAIL', 'next_action': 'FIX_REQUIRED', 'dispatch': True,
            'reserved_iteration': iteration + 1}
