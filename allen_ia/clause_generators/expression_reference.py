from typing import List, Callable, Optional

from allen_ia.clause import Clause
from allen_ia.expression_literal import ExpressionLiteral
from allen_ia.input.inverse_relationships_table import InverseRelationshipsTable, inverse_relationships_to_dict
from allen_ia.input.ternary_constraints_table import TernaryConstraintsTable, ternary_constraints_to_dict
from allen_ia.input.time_intervals_table import TimeIntervalsGroup, time_intervals_to_dict
from allen_ia.literal import Literal


def generate_expression_reference(group: TimeIntervalsGroup, table: TernaryConstraintsTable,
                                  inverse_table: InverseRelationshipsTable) -> List[Clause]:
    """
    Generate the clauses using the expression reference algorithm.

    :param group: the time intervals group to execute the algorithm on.
    :param table: the ternary constraints table.
    :param inverse_table: the inverse relationships table.
    :return: the generated clauses.
    """

    clauses: List[Clause] = []
    inverse_relationships_dict = inverse_relationships_to_dict(inverse_table)
    relationships_dict = ternary_constraints_to_dict(table)
    intervals_dict = time_intervals_to_dict(group)

    # Expand the intervals dictionary to include inverse mappings too.
    intervals_dict_ext = {}
    for (t_from, t_to), relationships in intervals_dict.items():
        intervals_dict_ext[(t_to, t_from)] = [inverse_relationships_dict[r] for r in relationships]
    intervals_dict.update(intervals_dict_ext)

    def generate_clause_for_triple(t1: int, t2: int, t3: int) -> Optional[List[Clause]]:
        """
        Generate the required clauses for a simple triple.

        :param t1: the first chosen time interval.
        :param t2: the second chosen time interval.
        :param t3: the third chosen time interval.
        :return: the generated clauses.
        """
        generated_clauses: List[Clause] = []

        if (t1, t2) not in intervals_dict:
            return
        if (t2, t3) not in intervals_dict:
            return
        if (t1, t3) not in intervals_dict:
            return

        t1_t2_relationships = intervals_dict[(t1, t2)]
        t2_t3_relationships = intervals_dict[(t2, t3)]

        for r_t1_t2 in t1_t2_relationships:
            clause: Clause = [Literal(t1, t2, r_t1_t2, True)]
            for r_t2_t3 in t2_t3_relationships:
                t1_t3_relationships = relationships_dict[(r_t1_t2, r_t2_t3)]

                for r_t1_t3 in t1_t3_relationships:
                    left_right_implication: Clause = []
                    right_left_implication_1: Clause = []
                    right_left_implication_2: Clause = []

                    # Use a proposition that demonstrates the implication from left to right.
                    left_right_implication.append(Literal(t2, t3, r_t2_t3, True))
                    left_right_implication.append(Literal(t1, t3, r_t1_t3, True))
                    left_right_implication.append(ExpressionLiteral(
                        Literal(t2, t3, r_t2_t3),
                        Literal(t1, t3, r_t1_t3)
                    ))

                    # Use a proposition that demonstrates the implication from right to left.
                    right_left_implication_1.append(Literal(t2, t3, r_t2_t3))
                    right_left_implication_1.append(ExpressionLiteral(
                        Literal(t2, t3, r_t2_t3),
                        Literal(t1, t3, r_t1_t3),
                        True
                    ))

                    right_left_implication_2.append(Literal(t1, t3, r_t1_t3))
                    right_left_implication_2.append(ExpressionLiteral(
                        Literal(t2, t3, r_t2_t3),
                        Literal(t1, t3, r_t1_t3),
                        True
                    ))

                    # Add all generated clauses to the master list.
                    generated_clauses.append(left_right_implication)
                    generated_clauses.append(right_left_implication_1)
                    generated_clauses.append(right_left_implication_2)

                # Add the clause we wanted to generate in the first place using
                # the previously generated expression literals.
                for r in t1_t3_relationships:
                    if ((t1, t3) in intervals_dict) and (r in intervals_dict[(t1, t3)]):
                        clause.append(ExpressionLiteral(
                            Literal(t2, t3, r_t2_t3),
                            Literal(t1, t3, r)
                        ))

            generated_clauses.append(clause)

        return generated_clauses

    n = group.total_time_intervals
    for i in range(n):
        for j in range(n):
            for k in range(n):
                if i == j or j == k or i == k:
                    continue
                generation_result = generate_clause_for_triple(i, j, k)
                if generation_result:
                    for clause in generation_result:
                        yield clause