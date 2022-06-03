from __future__ import annotations

import typing
from dataclasses import dataclass

T = typing.TypeVar("T")


class BooleanLogic:

    @dataclass
    class Operator(typing.Generic[T]):
        def evaluate(self, items: typing.List[T]) -> bool:
            pass

        def pprint(self, fmt=str):
            pass

    @dataclass
    class BinaryOperator(Operator):
        a: BooleanLogic.Operator
        b: BooleanLogic.Operator

    @dataclass
    class UnaryOperator(Operator):
        x: BooleanLogic.Operator

    @dataclass
    class ExecutionOperator(Operator):
        item: T
        predicate: typing.Callable

        def evaluate(self, items: typing.List[T]) -> bool:
            return self.predicate(self.item, items)

        def pprint(self, fmt=str):
            return fmt(self.item)

    class AndOperator(BinaryOperator):

        def evaluate(self, items: typing.List[T]) -> bool:
            return self.a.evaluate(items) and self.b.evaluate(items)

        def pprint(self, fmt=str):
            return f"({self.a.pprint(fmt)} AND {self.b.pprint(fmt)})"

    class OrOperator(BinaryOperator):

        def evaluate(self, items: typing.List[T]) -> bool:
            return self.a.evaluate(items) or self.b.evaluate(items)

        def pprint(self, fmt=str):
            return f"({self.a.pprint(fmt)} OR {self.b.pprint(fmt)})"

    class NotOperator(UnaryOperator):

        def evaluate(self, items: typing.List[T]) -> bool:
            return not self.x.evaluate(items)

        def pprint(self, fmt=str):
            return f"(NOT {self.x.pprint(fmt)})"

    class OperationBuilder:

        def __init__(self, inner_tokens: typing.List[typing.Union[str, T]],
                     predicate: typing.Callable[[typing.List[T], T], bool]):
            self.inner_tokens = inner_tokens
            self.iter_tokens = iter(inner_tokens)
            self.this_token = None
            self.predicate = predicate
            self.next_token()

        def next_token(self):
            try:
                self.this_token = next(self.iter_tokens)
            except StopIteration:
                self.this_token = None

        def build(self):
            if self.this_token is None:
                return None
            return self.build_inversion()

        def build_inversion(self):

            if self.this_token == "!":
                self.next_token()
                return BooleanLogic.NotOperator(self.build_and())
            else:
                return self.build_and()

        def build_and(self):
            result = self.build_or()
            while self.this_token is not None:
                if self.this_token == "&":
                    self.next_token()
                    if self.this_token == "&":
                        self.next_token()
                    result = BooleanLogic.AndOperator(result, self.build_or())
                else:
                    break
            return result

        def build_or(self):
            result = self.build_literal()

            while self.this_token is not None:
                if self.this_token == "|":
                    self.next_token()
                    if self.this_token == "|":
                        self.next_token()
                    result = BooleanLogic.OrOperator(result, self.build_literal())
                else:
                    break

            return result

        def build_literal(self):
            if self.this_token == "(":
                self.next_token()
                result = self.build_inversion()
                self.next_token()
                return result
            prev_token = self.this_token
            self.next_token()
            return BooleanLogic.ExecutionOperator(prev_token, self.predicate)
