from abm_model.loan import Loan
from abm_model.baseclass import BaseAgent
import numpy as np
import random


class BaseBank(BaseAgent):
    deposit_systemic_shock = None
    h_theta = None

    @classmethod
    def change_value_deposit_systemic(cls, new_value):
        cls.deposit_systemic_shock = new_value

    @classmethod
    def change_h_theta(cls, new_value):
        cls.h_theta = new_value


class Bank(BaseBank):
    def __init__(self,
                 idx,
                 equity,
                 deposits,
                 capital_requirement,
                 covered_cds_prob,
                 naked_cds_prob
                 ):
        super().__init__()
        self.idx = idx
        self.equity = equity
        self.deposits = deposits
        self.capital_requirement = capital_requirement
        self.covered_cds_prob = covered_cds_prob
        self.naked_cds_prob = naked_cds_prob
        self.max_credit = None
        self.assets = {'loans': [], 'cds': []}
        self.liabilities = {'loans': [], 'cds': []}

    def update_max_credit(self):
        self.max_credit = self.deposits / self.capital_requirement

    def asses_loan_requests(self, loans: list[Loan]):
        loan_offers = []
        for loan in loans:
            if loan.notional_amount > self.max_credit:
                continue
            if loan.borrower in self.firm_ids:
                loan.update_interest_rate(self.policy_rate * (1 + np.random.uniform(0, self.h_theta) *
                                                              np.tanh((1 + np.random.uniform(0.9, 1.1) *
                                                                       loan.prob_default_borrower) *
                                                                      loan.financial_fragility_borrower)))
                loan_offers.append(loan)
            else:  # we have an interbank loan
                # TODO: change function if needed
                loan.update_interest_rate(self.policy_rate * (1 + np.random.uniform(0, self.h_theta) *
                                                              np.tanh(loan.financial_fragility_borrower)))
                loan_offers.append(loan)
        return loan_offers

    def check_loan(self, loan):
        if (loan.notional_amount + sum([x.notional_amount for x in self.assets['loans']]) +
                sum([x.spread * x.notional_amount for x in self.assets['cds']]) > self.max_credit):
            return False
        return (self.deposits + sum([x.notional_amount for x in self.liabilities['loans']]) -
                (loan.notional_amount + sum([x.notional_amount for x in self.assets['loans']]) +
                 sum([x.spread * x.notional_amount for x in self.assets['cds']])))

    def check_cds(self, premium):
        return (self.deposits + sum([x.notional_amount for x in self.liabilities['loans']]) + self.equity -
                (sum([x.notional_amount for x in self.assets['loans']]) +
                 sum([x.spread * x.notional_amount for x in self.assets['cds']])) >= premium)

    def get_potential_interbank_loans(self, credit_needed, notional_amount):
        financial_fragility = (notional_amount + sum([x.notional_amount for x in self.assets['loans']])) / self.deposits
        return [Loan(lender=x, borrower=self.idx,
                     notional_amount=credit_needed,
                     financial_fragility_borrower=financial_fragility)
                for x in random.choices([x for x in self.bank_ids if x != self.idx], k=self.max_interbank_loan)
                ]

    def decide_cds(self, covered=True):
        if covered:
            return np.random.binomial(1, self.covered_cds_prob)
        else:
            return np.random.binomial(1, self.naked_cds_prob)

    def provide_cds_spread(self,loan):
        #add random noise to cds spread or use cds valuation method
        cds_tax = self.cds_tax(loan)
        return loan.prob_default_borrower + cds_tax

    #add cds tax function based on systemic risk
    def cds_tax(self, loan):
        return np.random.uniform(-0.00999999,0.04)