#!/usr/bin/env python3
import sys
import argparse
import ipaddress


def parse_args():
    p = argparse.ArgumentParser(
        description="Filter lines by whether an IP field matches one or more CIDRs."
    )

    p.add_argument(
        "-e", "--expr",
        action="append",
        default=[],
        help="CIDR expression to match; can be given multiple times"
    )
    p.add_argument(
        "-C", "--cidr-file",
        help="File containing CIDRs, one per line"
    )
    p.add_argument(
        "-v", "--invert-match",
        action="store_true",
        help="Select non-matching lines"
    )
    p.add_argument(
        "-c", "--count",
        action="store_true",
        help="Print only the number of selected lines"
    )
    p.add_argument(
        "-o", "--only-matching",
        action="store_true",
        help="Print only the selected IP field"
    )
    p.add_argument(
        "-f", "--field",
        type=int,
        default=1,
        help="1-based field number containing the IP (default: 1)"
    )

    # Trick:
    # We allow remaining positional args to contain:
    # - one or more CIDRs
    # - optionally the input filename as the last arg
    p.add_argument(
        "args",
        nargs="*",
        help="CIDRs followed optionally by input file"
    )

    return p.parse_args()


def load_cidrs(args):
    cidr_strings = []

    # from -e / --expr
    cidr_strings.extend(args.expr)

    # from file
    if args.cidr_file:
        try:
            with open(args.cidr_file, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    cidr_strings.append(line)
        except OSError as e:
            print(f"Cannot open CIDR file '{args.cidr_file}': {e}", file=sys.stderr)
            sys.exit(3)

    # from positional args:
    # interpret all but last as CIDRs if last is not a CIDR
    positional = list(args.args)
    infile = None

    if positional:
        maybe_last = positional[-1]
        try:
            ipaddress.ip_network(maybe_last, strict=False)
            # last arg is also a CIDR -> all positional args are CIDRs, input is stdin
            cidr_strings.extend(positional)
        except ValueError:
            # last arg is probably a filename
            infile = maybe_last
            cidr_strings.extend(positional[:-1])

    if not cidr_strings:
        print("No CIDRs provided.", file=sys.stderr)
        sys.exit(2)

    networks = []
    for cidr in cidr_strings:
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError as e:
            print(f"Invalid CIDR: {cidr} ({e})", file=sys.stderr)
            sys.exit(2)

    return networks, infile


def ip_matches_any(ip_s, networks):
    try:
        ip = ipaddress.ip_address(ip_s)
    except ValueError:
        return False

    for net in networks:
        if ip.version == net.version and ip in net:
            return True
    return False


def main():
    args = parse_args()

    if args.field < 1:
        print("Field number must be >= 1", file=sys.stderr)
        sys.exit(2)

    networks, infile = load_cidrs(args)

    fh = sys.stdin
    if infile:
        try:
            fh = open(infile, "r", encoding="utf-8", errors="ignore")
        except OSError as e:
            print(f"Cannot open file '{infile}': {e}", file=sys.stderr)
            sys.exit(3)

    selected = 0
    field_index = args.field - 1

    try:
        for line in fh:
            if not line.strip():
                continue

            parts = line.split()
            if field_index >= len(parts):
                continue

            ip_s = parts[field_index]
            matched = ip_matches_any(ip_s, networks)

            if args.invert_match:
                matched = not matched

            if matched:
                selected += 1
                if not args.count:
                    if args.only_matching:
                        print(ip_s)
                    else:
                        print(line, end="")
    finally:
        if fh is not sys.stdin:
            fh.close()

    if args.count:
        print(selected)


if __name__ == "__main__":
    main()
