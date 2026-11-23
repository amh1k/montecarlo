#!/usr/bin/env python3
"""Build the PDF report with ReportLab from recorded results and figures."""

import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "2026-11-23"
FIGURES = ROOT / "results" / "figures"
OUTPUT = Path(__file__).with_name("Monte-Carlo-Report.pdf")
MARGIN = 48
WIDTH = A4[0] - 2 * MARGIN - 12
INK = colors.HexColor("#172932")
MUTED = colors.HexColor("#425764")
ACCENT = colors.HexColor("#116760")
LINE = colors.HexColor("#CFDBDF")
TINT = colors.HexColor("#EFF5F4")

BODY = ParagraphStyle("Body", fontName="Helvetica", fontSize=10.3, leading=15,
                      textColor=INK, spaceAfter=8)
CAPTION = ParagraphStyle("Caption", parent=BODY, fontSize=9, leading=12,
                         textColor=MUTED, spaceAfter=10)
HEADING = ParagraphStyle("Heading", parent=BODY, fontName="Helvetica-Bold",
                         fontSize=19, leading=23, spaceBefore=3, spaceAfter=8)
TITLE = ParagraphStyle("Title", parent=HEADING, fontSize=34, leading=37, spaceAfter=11)
LABEL = ParagraphStyle("Label", parent=BODY, fontName="Helvetica-Bold", fontSize=9,
                       leading=11, textColor=ACCENT, spaceAfter=8)
CODE = ParagraphStyle("Code", parent=BODY, fontName="Courier", fontSize=8.1,
                      leading=12, leftIndent=10, spaceBefore=3)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=9, leading=12, spaceAfter=0)
HEADER = ParagraphStyle("Header", parent=CELL, fontName="Helvetica-Bold",
                        textColor=colors.white)


def read_rows(filename):
    with (RESULTS / filename).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def table(headings, rows, widths):
    data = [[Paragraph(heading, HEADER) for heading in headings]]
    data.extend([Paragraph(str(value), CELL) for value in row] for row in rows)
    result = Table(data, colWidths=widths, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, TINT]),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return result


def figure(filename, caption):
    path = FIGURES / filename
    original_width, original_height = ImageReader(str(path)).getSize()
    width = 462
    chart = Image(str(path), width=width, height=width * original_height / original_width)
    return [chart, Paragraph(caption, CAPTION)]


def footer(canvas, document):
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN, 43, A4[0] - MARGIN, 43)
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 29, "PDC PROJECT 7  /  PARALLEL MONTE CARLO")
    canvas.drawRightString(A4[0] - MARGIN, 29, str(document.page))


def main():
    scaling = read_rows("scaling_summary.csv")
    accuracy = read_rows("accuracy_summary.csv")
    excluded = read_rows("excluded_third_repetition.csv")
    baseline = next(float(row["median_seconds"]) for row in scaling if row["mode"] == "seq")
    third = next(float(row["seconds"]) for row in excluded if row["mode"] == "seq")
    modes = {"seq": "Sequential", "omp": "OpenMP", "mpi": "MPI", "hybrid": "Hybrid"}
    performance = [
        (modes[row["mode"]], row["ranks"], row["threads_per_rank"],
         f'{float(row["median_seconds"]):.2f}',
         f'{float(row["min_seconds"]):.2f} to {float(row["max_seconds"]):.2f}',
         f'{float(row["speedup"]):.2f}', f'{float(row["efficiency"]):.2f}')
        for row in scaling
    ]
    endpoints = {
        (row["mode"], int(row["trials"])): float(row["root_mean_squared_error"])
        for row in accuracy
    }

    story = [
        Paragraph("PARALLEL AND DISTRIBUTED COMPUTING  /  PROJECT 7", LABEL),
        Paragraph("Parallel Monte Carlo<br/>estimation of pi", TITLE),
        Paragraph("Huzaifa Abdul Rehman (23K-0782)  &nbsp; Abdul Moiz Hussain (23K-0553)<br/>"
                  "Muhammad Abdullah Khan (23K-0607)  &nbsp; | &nbsp; 23 November 2026", BODY),
        Spacer(1, 6),
        Paragraph("1. Objective and design", HEADING),
        Paragraph("We measured how OpenMP threads, MPI ranks, and combinations of both affect the "
                  "runtime of a fixed Monte Carlo workload. We also varied the number of samples and "
                  "seeds to see how the estimation error changes.", BODY),
        Paragraph("Each trial draws two pseudorandom coordinates from [0, 1) and records a hit when "
                  "x<super>2</super> + y<super>2</super> is at most 1. The quarter-circle occupies pi/4 "
                  "of the unit square, so the estimate is 4H/N for H hits from N trials. "
                  "Each worker keeps private SplitMix64 state derived from the seed, rank and thread IDs. "
                  "Fixed inputs and layout reproduce the hit count. Each point is discarded after use, "
                  "keeping per-worker storage constant as N grows.", BODY),
        table(["Mode", "Work distribution and aggregation"], [
            ("Sequential", "One worker runs all N trials and reports the local count."),
            ("OpenMP", "A static loop divides N trials among threads. An integer reduction sums the counts."),
            ("MPI", "Of P ranks, rank r gets floor(N/P) trials plus one if r &lt; N mod P. A 64-bit MPI sum combines counts at rank zero."),
            ("Hybrid", "MPI divides trials among ranks. Each rank runs a static OpenMP loop, then MPI combines the rank totals."),
        ], [92, WIDTH - 92]),
        Spacer(1, 9),
        Paragraph("The C17 executables share sampling code, unsigned 64-bit input and count handling, "
                  "and CSV output. Ranks assigned zero trials still join the collectives. Hybrid "
                  "requests MPI_THREAD_FUNNELED, calls MPI on the main thread, and checks that the "
                  "ranks report the same OpenMP team size.", BODY),
        Paragraph("2. Experimental protocol", HEADING),
        Paragraph("We used GCC 15.2.0 with OpenMP via <font name='Courier'>-fopenmp</font> and MPICH 4.3.2 "
                  "on one Intel Core i7-8650U host under WSL2. The guest exposed four physical cores "
                  "and eight logical CPUs. Placement selected CPU IDs 0, 2, 4 and 6, assigned disjoint "
                  "CPU sets to MPI ranks, and bound OpenMP threads to cores.", BODY),
        Paragraph("Ten layouts ran a 10<super>7</super>-trial pilot and two retained scaling repetitions "
                  "at 10<super>10</super> trials with seed 42. The accuracy sweep used four trial counts "
                  "and five seeds across four layouts, for 80 measurements. All baseline layouts completed.", BODY),
        Paragraph("In a fresh build, all four single-worker runs returned 785,674 hits for one million "
                  "trials with seed 42. MPI and hybrid finished both uneven work splits (10 trials over "
                  "3 ranks and 2 trials over 4 ranks). The Python suite passed all 11 tests.", BODY),
        PageBreak(),
        Paragraph("3. Measured runtime", HEADING),
        Paragraph("The sequential timer measures sampling. OpenMP includes team creation and summing "
                  "thread counts. MPI and hybrid synchronize before starting the timer and report the "
                  "maximum rank duration through the hit-count reduction. The reported times exclude "
                  "process launch, argument handling, and printing. The sequential run reported 7,853,999,959 "
                  "hits, exceeding the unsigned 32-bit range.", BODY),
        table(["Mode", "Ranks", "Threads<br/>per rank", "Median<br/>(s)", "Min to max (s)", "Speedup", "Efficiency"],
              performance, [73, 42, 58, 58, 93, 65, WIDTH - 389]),
        Spacer(1, 8),
        Paragraph("Table 1. Two retained 10-billion-trial runs per layout. Speedup is sequential median "
                  "time divided by layout median time. Efficiency is speedup divided by ranks times "
                  "threads per rank. The two endpoints show the observed spread.", CAPTION),
        *figure("runtime.png", "Figure 1. Median estimator runtime by layout at equal trial count and seed."),
        Paragraph("OpenMP with four threads had the lowest retained median (29.84 s), followed by "
                  "four MPI ranks (31.70 s). The hybrid layouts used four workers throughout, with medians "
                  "from 33.56 s for 1 rank with 4 threads to 35.72 s for 4 ranks with 1 thread.", BODY),
        PageBreak(),
        Paragraph("4. Speedup and efficiency", HEADING),
        *figure("speedup.png", f"Figure 2. Measured speedup relative to the {baseline:.2f} s sequential median. "
                "The ideal markers equal the worker count."),
        *figure("efficiency.png", "Figure 3. Speedup divided by total workers. The reference line marks efficiency of 1."),
        Paragraph(f"A third round stopped after the protocol switched to two repetitions. Its completed "
                  f"sequential run took {third:.2f}&nbsp;s, {(1 - third / baseline):.0%} below the retained "
                  f"{baseline:.2f}&nbsp;s sequential median. The separate record shows variability beyond "
                  "the retained range. Several reported efficiencies exceed 1, but two repetitions "
                  "give little basis for claiming superlinear scaling. CPU frequency and host scheduling "
                  "were uncontrolled. On this single host, MPI performance includes local synchronization "
                  "and reduction costs. The timing did not isolate those costs or measure network scaling.", BODY),
        PageBreak(),
        Paragraph("5. Accuracy and conclusions", HEADING),
        Paragraph("For independent uniform trials, H is binomial with success probability p = pi/4. "
                  "The standard deviation of 4H/N is 4 sqrt(p(1 - p)/N), which falls as 1/sqrt(N). "
                  "We calculated root mean squared error (RMSE) against pi over seeds 0, 1, 2, 3 and 42 "
                  "at N = 10<super>4</super>, 10<super>5</super>, 10<super>6</super> and 10<super>7</super>. "
                  "The layouts were sequential, OpenMP with 4 threads, MPI with 4 ranks, and hybrid "
                  "with 2 ranks and 2 threads per rank.", BODY),
        *figure("accuracy.png", "Figure 4. Empirical RMSE across five seeds per point on logarithmic axes, "
                "with the expected inverse-square-root reference."),
        Paragraph("From 10<super>4</super> to 10<super>7</super> trials, RMSE fell from "
                  + ", ".join(f'{endpoints[mode, 10**4]:.4f} to {endpoints[mode, 10**7]:.5f} ({name})'
                              for mode, name in modes.items())
                  + ". OpenMP error rose slightly between the first two trial counts. Five seeds per "
                    "layout and trial count give an imprecise estimate of the error curve.", BODY),
        Paragraph("All four implementations completed the required 10-billion-trial workload. Four-worker "
                  "layouts reduced measured runtime on this host, and every mode had the lowest RMSE at the "
                  "largest tested sample size. Controlled repeats and additional seeds would help quantify "
                  "the size and stability of these effects.", BODY),
        Paragraph("Reproduce a small run", LABEL),
        Preformatted(
            "make seq omp mpi hybrid\n"
            "./build/seq 1000000 42\n"
            "OMP_NUM_THREADS=4 OMP_DYNAMIC=FALSE ./build/omp 1000000 42\n"
            "mpiexec -n 4 ./build/mpi 1000000 42\n"
            "OMP_NUM_THREADS=2 OMP_DYNAMIC=FALSE mpiexec -n 2 ./build/hybrid 1000000 42",
            CODE,
        ),
        Paragraph("The repository README gives build and experiment commands. The raw CSV, invocation logs, "
                  "machine metadata, effective protocol and derived summaries are under "
                  "<font name='Courier'>results/2026-11-23/</font>.", CAPTION),
    ]
    report = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=47, bottomMargin=52, title="Parallel Monte Carlo estimation of pi",
        author="Huzaifa Abdul Rehman, Abdul Moiz Hussain, and Muhammad Abdullah Khan",
        invariant=1,
    )
    report.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    main()
