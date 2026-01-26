class ResumeOptimizerStateMachine:
    def __init__(self):
        self.state = "start"
        self.transitions = {
            "start": {
                "select_user": ("waiting_job_description", "User setup finished."),
            },
            "waiting_job_description": {
                "submit_jd": ("analyzing", "Analyzing resume against job description..."),
            },
            "analyzing": {
                "analysis_complete": ("reviewing_analysis", "Analysis complete. Review keywords and scores."),
                "error": ("waiting_job_description", "Analysis failed."),
            },
            "reviewing_analysis": {
                "start_optimization": ("optimizing", "Optimizing resume based on analysis..."),
                "back": ("waiting_job_description", "Returning to JD input."),
            },
            "optimizing": {
                "finished": ("job_exploration", "Optimization complete!"),
                "error": ("reviewing_analysis", "Optimization failed."),
            },
            "job_exploration": {
                "reset": ("waiting_job_description", "Starting over..."),
            }
        }

    def next(self, event):
        if event in self.transitions.get(self.state, {}):
            next_state, message = self.transitions[self.state][event]
            self.state = next_state
            return message
        else:
            return f"Event: '{event}' -> is not valid for actual state: '{self.state}'."

    def reset(self):
        self.state = "start"