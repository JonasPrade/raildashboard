from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Float, Text, Index
from sqlalchemy.orm import relationship, backref

from dashboard_backend.models.base import Base


class Budget(Base):
    __tablename__ = 'budgets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    budget_year = Column(Integer, nullable=False)
    lfd_nr = Column(String(100))
    fin_ve = Column(Integer, ForeignKey('finve.id'))
    bedarfsplan_number = Column(String(100))
    sammel_finve = Column(Boolean, default=False)

    starting_year = Column(Integer)
    cost_estimate_original = Column(Integer)
    cost_estimate_last_year = Column(Integer)

    cost_estimate_actual = Column(Integer)
    cost_estimate_actual_third_parties = Column(Integer)
    cost_estimate_actual_equity = Column(Integer)  # Eigenanteil EIU
    cost_estimate_actual_891_01 = Column(Integer)
    cost_estimate_actual_891_02 = Column(Integer)
    cost_estimate_actual_891_03 = Column(Integer)
    cost_estimate_actual_891_04 = Column(Integer)
    cost_estimate_actual_891_91 = Column(Integer)
    cost_estimate_actual_891_72 = Column(Integer)
    cost_estimate_actual_891_11 = Column(Integer)
    cost_estimate_actual_891_21 = Column(Integer)
    cost_estimate_actual_861_01 = Column(Integer)

    delta_previous_year = Column(Integer)
    delta_previous_year_relativ = Column(Float)
    delta_previous_year_reasons = Column(Text)

    spent_two_years_previous = Column(Integer)
    spent_two_years_previous_third_parties = Column(Integer)
    spent_two_years_previous_equity = Column(Integer)
    spent_two_years_previous_891_01 = Column(Integer)
    spent_two_years_previous_891_02 = Column(Integer)
    spent_two_years_previous_891_03 = Column(Integer)
    spent_two_years_previous_891_04 = Column(Integer)
    spent_two_years_previous_891_91 = Column(Integer)
    spent_two_years_previous_891_72 = Column(Integer)
    spent_two_years_previous_891_11 = Column(Integer)
    spent_two_years_previous_891_21 = Column(Integer)
    spent_two_years_previous_861_01 = Column(Integer)

    allowed_previous_year = Column(Integer)
    allowed_previous_year_third_parties = Column(Integer)
    allowed_previous_year_equity = Column(Integer)
    allowed_previous_year_891_01 = Column(Integer)
    allowed_previous_year_891_02 = Column(Integer)
    allowed_previous_year_891_03 = Column(Integer)
    allowed_previous_year_891_04 = Column(Integer)
    allowed_previous_year_891_91 = Column(Integer)
    allowed_previous_year_891_72 = Column(Integer)
    allowed_previous_year_891_11 = Column(Integer)
    allowed_previous_year_891_21 = Column(Integer)
    allowed_previous_year_861_01 = Column(Integer)

    spending_residues = Column(Integer)
    spending_residues_891_01 = Column(Integer)
    spending_residues_891_02 = Column(Integer)
    spending_residues_891_03 = Column(Integer)
    spending_residues_891_04 = Column(Integer)
    spending_residues_891_91 = Column(Integer)
    spending_residues_891_72 = Column(Integer)
    spending_residues_891_11 = Column(Integer)
    spending_residues_891_21 = Column(Integer)
    spending_residues_861_01 = Column(Integer)

    year_planned = Column(Integer)
    year_planned_third_parties = Column(Integer)
    year_planned_equity = Column(Integer)
    year_planned_891_01 = Column(Integer)
    year_planned_891_02 = Column(Integer)
    year_planned_891_03 = Column(Integer)
    year_planned_891_04 = Column(Integer)
    year_planned_891_91 = Column(Integer)
    year_planned_891_72 = Column(Integer)
    year_planned_891_11 = Column(Integer)
    year_planned_891_21 = Column(Integer)
    year_planned_861_01 = Column(Integer)

    next_years = Column(Integer)
    next_years_third_parties = Column(Integer)
    next_years_equity = Column(Integer)
    next_years_891_01 = Column(Integer)
    next_years_891_02 = Column(Integer)
    next_years_891_03 = Column(Integer)
    next_years_891_04 = Column(Integer)
    next_years_891_91 = Column(Integer)
    next_years_891_72 = Column(Integer)
    next_years_891_11 = Column(Integer)
    next_years_891_21 = Column(Integer)
    next_years_861_01 = Column(Integer)

    finve = relationship("Finve", backref=backref("budgets"))
    __table_args__ = (
        Index('budgets_year_and_finve_uindex', "budget_year", "fin_ve", unique=True),
    )
