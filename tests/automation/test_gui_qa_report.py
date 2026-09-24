import importlib.util,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'scripts/gui_qa/report.py'
s=importlib.util.spec_from_file_location('gui_report',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class GuiReportTests(unittest.TestCase):
    def test_unit_success_without_actual_gui_event_is_not_gui_pass(self):
        record={'documentContainsAll':True,'frontmostAlwaysTextEdit':True,'focusedRoles':['AXTextArea']}
        self.assertEqual(m.focus_result(record,False),'ENVIRONMENT_UNAVAILABLE')
        self.assertEqual(m.focus_result(record,True),'GUI_AUTO_PASS')
    def test_lost_input_focus_or_permission_cannot_pass(self):
        self.assertEqual(m.focus_result(None,True),'PERMISSION_REQUIRED')
        for record in [{},{'documentContainsAll':False,'frontmostAlwaysTextEdit':True,'focusedRoles':['AXTextArea']},{'documentContainsAll':True,'frontmostAlwaysTextEdit':False,'focusedRoles':['AXTextArea']}]:
            self.assertEqual(m.focus_result(record,True),'FAIL')
    def test_counts_remain_separate(self):
        rows=[{'result':r} for r in m.RESULTS]
        self.assertEqual(m.summarize(rows),{'pass':2,'fail':1,'permissionRequired':1,'environmentUnavailable':1,'manualVisualReview':1})
