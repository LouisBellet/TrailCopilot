from core.training_db import get_all_activities, get_user_profile
from core.workload_engine import WorkloadEngine
from core.coach_engine import CoachEngine

class DataManager:
    _activities = None
    _profile = None
    _readiness = None
    _summary_7d = None
    _coach_advice = None
    _dirty_tabs = set()

    @classmethod
    def invalidate_cache(cls):
        cls._activities = None
        cls._readiness = None
        cls._summary_7d = None
        cls._coach_advice = None
        cls._dirty_tabs = {0, 1, 2, 3}

    @classmethod
    def get_activities(cls):
        if cls._activities is None:
            cls._activities = get_all_activities()
        return cls._activities

    @classmethod
    def get_profile(cls):
        if cls._profile is None:
            cls._profile = get_user_profile()
        return cls._profile

    @classmethod
    def get_readiness(cls):
        if cls._readiness is None:
            acts = cls.get_activities()
            cls._readiness = WorkloadEngine.compute_readiness(acts)
            advice = cls.get_coach_advice()
            cls._readiness["projections"] = advice.get("projections", [])
            cls._readiness["target_budget"] = advice.get("target_budget", 0.0)
        return cls._readiness

    @classmethod
    def get_summary_7d(cls):
        if cls._summary_7d is None:
            acts = cls.get_activities()
            cls._summary_7d = CoachEngine.compute_7day_summary(acts)
        return cls._summary_7d

    @classmethod
    def get_coach_advice(cls):
        if cls._coach_advice is None:
            acts = cls.get_activities()
            prof = cls.get_profile()
            if cls._readiness is None:
                cls._readiness = WorkloadEngine.compute_readiness(acts)
            cls._coach_advice = CoachEngine.compute_daily_advice(acts, prof, cls._readiness["acwr"])
        return cls._coach_advice

    @classmethod
    def is_tab_dirty(cls, tab_index: int) -> bool:
        return tab_index in cls._dirty_tabs

    @classmethod
    def mark_tab_clean(cls, tab_index: int):
        cls._dirty_tabs.discard(tab_index)