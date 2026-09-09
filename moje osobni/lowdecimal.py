
import math
import re
from contextlib import contextmanager

_NUMBER = re.compile(r"\A([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?\Z")


def _add_digits(a, b):
    out = []
    carry = 0
    for x in range(len(a) - 1, -1, -1):
        total = int(a[x]) + int(b[x]) + carry
        carry = total // 10
        out.append(str(total % 10))
    out.reverse()
    return carry, "".join(out)


def _sub_digits(a, b):
    out = []
    borrow = 0
    for x in range(len(a) - 1, -1, -1):
        total = int(a[x]) - int(b[x]) - borrow
        if total < 0:
            total += 10
            borrow = 1
        else:
            borrow = 0
        out.append(str(total))
    out.reverse()
    return "".join(out)


def _round_digits(digits, exp, keep):
    if len(digits) <= keep:
        return digits.ljust(keep, "0"), exp
    kept = digits[:keep]
    if digits[keep] >= "5":
        carry, kept = _add_digits(kept, "0" * (keep - 1) + "1")
        if carry:
            kept = "1" + kept[:-1]
            exp += 1
    return kept, exp


@contextmanager
def working_precision(digits):
    previous = lowdecimal.PRECISION
    lowdecimal.PRECISION = digits
    try:
        yield
    finally:
        lowdecimal.PRECISION = previous


def _parse_text(text):
    match = _NUMBER.match(text)
    if match is None or not (match.group(2) or match.group(3)):
        raise ValueError("cannot read %r as a lowdecimal" % (text,))
    sign = -1 if match.group(1) == "-" else 1
    intpart = match.group(2) or ""
    fracpart = match.group(3) or ""
    # the point sits after len(intpart) digits, so this is the exponent of the
    # first digit of intpart + fracpart (leading zeros are dropped in _set)
    exp = len(intpart) - 1 + int(match.group(4) or 0)
    return sign, intpart + fracpart, exp


class lowdecimal:

    PRECISION = 64      # significant digits stored in self.digits
    ROUND_GUARD = 2     # digits below the last one that can still change it
    SPARE = 10          # working digits the multi-step methods add and drop

    __slots__ = ("sign", "digits", "exp")

    def __init__(self, value=0):
        if isinstance(value, lowdecimal):
            self.sign, self.digits, self.exp = value.sign, value.digits, value.exp
            return
        # repr() of a float is the shortest string that round-trips; the float
        # was already imprecise before it got here, this does not make it worse
        text = repr(value) if isinstance(value, float) else str(value).strip()
        self._set(*_parse_text(text))

    # --------------------------------------------------------------- internals

    def _set(self, sign, digits, exp):
        """Normalise: no leading zero, exactly PRECISION digits."""
        stripped = digits.lstrip("0")
        if not stripped:
            self.sign, self.digits, self.exp = 1, "0" * self.PRECISION, 0
            return
        exp -= len(digits) - len(stripped)
        self.digits, self.exp = _round_digits(stripped, exp, self.PRECISION)
        self.sign = 1 if sign >= 0 else -1

    @classmethod
    def _make(cls, sign, digits, exp):
        """Build a value from a raw digit string of any length."""
        new = cls.__new__(cls)
        new._set(sign, digits, exp)
        return new

    @classmethod
    def _coerce(cls, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, (int, float, str)):
            return cls(value)
        return None

    def _cmp_size(self, other):
        """Compare magnitudes only: -1, 0 or 1."""
        if self.exp != other.exp:
            return 1 if self.exp > other.exp else -1
        if self.digits != other.digits:
            # equal length, so a plain string compare is a numeric compare
            return 1 if self.digits > other.digits else -1
        return 0

    # ------------------------------------------------------------------ queries

    def is_zero(self):
        return self.digits[0] == "0"

    def copy(self):
        return lowdecimal(self)

    # --------------------------------------------------------------- arithmetic

    def neg(self):
        if self.is_zero():
            return lowdecimal(self)
        return lowdecimal._make(-self.sign, self.digits, self.exp)

    def abs(self):
        return lowdecimal._make(1, self.digits, self.exp)

    def add(self, other):
        other = self._coerce(other)
        if other is None:
            raise TypeError("cannot add that to a lowdecimal")
        if self.is_zero():
            return lowdecimal(other)
        if other.is_zero():
            return lowdecimal(self)

        if self._cmp_size(other) >= 0:
            big, small = self, other
        else:
            big, small = other, self

        shift = big.exp - small.exp
        if shift > self.PRECISION + self.ROUND_GUARD:
            return lowdecimal(big)      # small sits below the last kept digit

        # line the two up on big.exp; both strings then hold the exact value
        big_row = big.digits + "0" * shift
        small_row = "0" * shift + small.digits

        if big.sign == small.sign:
            carry, total = _add_digits(big_row, small_row)
            if carry:
                return lowdecimal._make(big.sign, "1" + total, big.exp + 1)
            return lowdecimal._make(big.sign, total, big.exp)

        # opposite signs: the bigger one keeps its sign, and any leading zeros
        # the subtraction leaves behind pull the exponent down in _set
        return lowdecimal._make(big.sign, _sub_digits(big_row, small_row), big.exp)

    def sub(self, other):
        other = self._coerce(other)
        if other is None:
            raise TypeError("cannot subtract that from a lowdecimal")
        return self.add(other.neg())

    def mul(self, other):
        other = self._coerce(other)
        if other is None:
            raise TypeError("cannot multiply a lowdecimal by that")
        if self.is_zero() or other.is_zero():
            return lowdecimal(0)
        # int() of the digit strings is exact (Python ints are unbounded), so
        # this is schoolbook long multiplication without the bookkeeping
        product = str(int(self.digits) * int(other.digits))
        exp = self.exp + other.exp + len(product) - 1 - 2 * (self.PRECISION - 1)
        return lowdecimal._make(self.sign * other.sign, product, exp)

    def div(self, other):
        other = self._coerce(other)
        if other is None:
            raise TypeError("cannot divide a lowdecimal by that")
        if other.is_zero():
            raise ZeroDivisionError("lowdecimal division by zero")
        if self.is_zero():
            return lowdecimal(0)
        # a couple of digits past the end so the rounding digit is itself right
        extra = self.PRECISION + self.ROUND_GUARD
        quotient = str(int(self.digits) * 10 ** extra // int(other.digits))
        exp = self.exp - other.exp + len(quotient) - 1 - extra
        return lowdecimal._make(self.sign * other.sign, quotient, exp)

    def power(self, n):
        """Raise to a whole power (exponentiation by squaring)."""
        if not isinstance(n, int):
            raise TypeError("lowdecimal powers must be whole numbers")
        # squaring rounds once per pass, and 1/x for x just over 1 lands just
        # under 1 and gains a digit place, so both run on spare digits
        text = self.to_string(trim=False)
        with working_precision(self.PRECISION + self.SPARE):
            result, base = lowdecimal(1), lowdecimal(text)
            todo = abs(n)
            while todo:
                if todo & 1:
                    result = result.mul(base)
                base = base.mul(base)
                todo >>= 1
            if n < 0:
                result = lowdecimal(1).div(result)
            long_result = result.to_string(trim=False)
        return lowdecimal(long_result)

    def sqrt(self):
        """Square root by Newton's method (correct digits double each pass)."""
        if self.is_zero():
            return lowdecimal(0)
        if self.sign < 0:
            raise ValueError("square root of a negative lowdecimal")
        text = self.to_string(trim=False)
        with working_precision(self.PRECISION + self.SPARE):
            value = lowdecimal(text)
            # split the exponent so the float starting guess cannot overflow:
            # the mantissa is left in [1, 100), the halved exponent put back
            half, rest = divmod(value.exp, 2)
            seed = lowdecimal(math.sqrt(float(lowdecimal._make(1, value.digits, rest))))
            guess = lowdecimal._make(seed.sign, seed.digits, seed.exp + half)

            two = lowdecimal(2)
            previous = None
            for _ in range(100):
                better = value.div(guess).add(guess).div(two)
                if better.compare(guess) == 0:
                    break
                if previous is not None and better.compare(previous) == 0:
                    break           # stuck between two neighbouring values
                previous, guess = guess, better
            long_root = better.to_string(trim=False)
        return lowdecimal(long_root)

    # --------------------------------------------------------------- comparison

    def compare(self, other):
        """-1 if self < other, 0 if equal, 1 if self > other."""
        other = self._coerce(other)
        if other is None:
            raise TypeError("cannot compare a lowdecimal with that")
        if self.is_zero():
            return 0 if other.is_zero() else -other.sign
        if other.is_zero():
            return self.sign
        if self.sign != other.sign:
            return self.sign
        return self.sign * self._cmp_size(other)

    # ------------------------------------------------------------------- output

    def to_string(self, trim=True):
        """Scientific form, e.g. '-1.234E-07'."""
        digits = self.digits
        if trim:
            digits = digits.rstrip("0") or "0"
        sign = "-" if self.sign < 0 else ""
        point = "." + digits[1:] if len(digits) > 1 else ""
        return "%s%s%s%s%s%02d" % (
            sign, digits[0], point,
            "E", "+" if self.exp >= 0 else "-", abs(self.exp))

    def plain(self, trim=True):
        """Ordinary positional form, e.g. '-0.0000001234'."""
        digits = self.digits
        if trim:
            digits = digits.rstrip("0") or "0"
        sign = "-" if self.sign < 0 else ""
        if self.exp < 0:
            return sign + "0." + "0" * (-self.exp - 1) + digits
        if self.exp + 1 >= len(digits):
            return sign + digits + "0" * (self.exp + 1 - len(digits))
        return sign + digits[:self.exp + 1] + "." + digits[self.exp + 1:]

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return "lowdecimal(%r)" % (self.to_string(),)

    def __float__(self):
        return float(self.to_string())

    def __int__(self):
        return int(self.plain().split(".")[0])

    def __bool__(self):
        return not self.is_zero()

    def __hash__(self):
        return hash((self.sign, self.digits, self.exp))

    # ----------------------------------------------------------------- operators

    def _binary(self, other, method):
        other = self._coerce(other)
        if other is None:
            return NotImplemented
        return method(self, other)

    def __add__(self, other):
        return self._binary(other, lowdecimal.add)

    def __sub__(self, other):
        return self._binary(other, lowdecimal.sub)

    def __mul__(self, other):
        return self._binary(other, lowdecimal.mul)

    def __truediv__(self, other):
        return self._binary(other, lowdecimal.div)

    def __radd__(self, other):
        return self._binary(other, lambda a, b: b.add(a))

    def __rsub__(self, other):
        return self._binary(other, lambda a, b: b.sub(a))

    def __rmul__(self, other):
        return self._binary(other, lambda a, b: b.mul(a))

    def __rtruediv__(self, other):
        return self._binary(other, lambda a, b: b.div(a))

    def __pow__(self, n):
        return self.power(n)

    def __neg__(self):
        return self.neg()

    def __pos__(self):
        return lowdecimal(self)

    def __abs__(self):
        return self.abs()

    def _compare_op(self, other, wanted):
        other = self._coerce(other)
        if other is None:
            return NotImplemented
        return self.compare(other) in wanted

    def __eq__(self, other):
        return self._compare_op(other, (0,))

    def __ne__(self, other):
        return self._compare_op(other, (-1, 1))

    def __lt__(self, other):
        return self._compare_op(other, (-1,))

    def __le__(self, other):
        return self._compare_op(other, (-1, 0))

    def __gt__(self, other):
        return self._compare_op(other, (1,))

    def __ge__(self, other):
        return self._compare_op(other, (0, 1))

    # ----------------------------------------------------------------- constants

    @classmethod
    def _atan_inv(cls, n):
        """atan(1/n) = 1/n - 1/(3n^3) + 1/(5n^5) - ... for a whole n > 1."""
        squared = cls(n * n)
        power = cls(1).div(cls(n))          # 1/n**k for k = 1, 3, 5, ...
        total = cls(0)
        k = 1
        sign = 1
        while True:
            piece = power.div(cls(k))
            if (not total.is_zero()
                    and total.exp - piece.exp > cls.PRECISION + cls.ROUND_GUARD):
                return total        # the term no longer reaches the digits we keep
            total = total.add(piece) if sign > 0 else total.sub(piece)
            power = power.div(squared)
            k += 2
            sign = -sign

    @classmethod
    def pi(cls):
        """Machin's formula: pi = 16*atan(1/5) - 4*atan(1/239).

        Summing ~50 terms rounds ~50 times, which is enough to spoil the last
        digit, so the series runs on spare digits that are then rounded off.
        """
        with working_precision(cls.PRECISION + cls.SPARE):
            long_pi = cls._atan_inv(5).mul(16).sub(cls._atan_inv(239).mul(4))
            text = long_pi.to_string(trim=False)
        return cls(text)


if __name__ == "__main__":
    # both checked against the decimal module at 200 digits, rounded to 64
    SQRT2 = "1.414213562373095048801688724209698078569671875376948073176679738"
    PI = "3.141592653589793238462643383279502884197169399375105820974944592"

    print("0.1 + 0.2  =", (lowdecimal("0.1") + lowdecimal("0.2")).plain())
    print("1 / 3      =", (lowdecimal(1) / 3).plain())
    print("sqrt(2)    =", lowdecimal(2).sqrt().plain())
    print("pi         =", lowdecimal.pi().plain())
    print("2 ** -40   =", (lowdecimal(2) ** -40).plain())
    print("1e30 + 1   =", (lowdecimal("1e30") + 1).plain())

    assert (lowdecimal("0.1") + lowdecimal("0.2")).plain() == "0.3"
    assert lowdecimal(2).sqrt().plain() == SQRT2
    assert lowdecimal.pi().plain() == PI
    assert abs(lowdecimal(2).sqrt() ** 2 - 2) < lowdecimal("1e-62")
    assert lowdecimal(1) / 7 * 7 == lowdecimal(1)
    assert lowdecimal("-2.5") < lowdecimal("-0.0001") < lowdecimal(0) < lowdecimal("1e-60")
    assert lowdecimal("1e30") + 1 - lowdecimal("1e30") == lowdecimal(1)
    assert abs(lowdecimal("-7.25")) == lowdecimal("7.25")
    assert float(lowdecimal("1.5e-3")) == 0.0015
    assert int(lowdecimal("-9.99")) == -9
    print("\nall checks passed")
