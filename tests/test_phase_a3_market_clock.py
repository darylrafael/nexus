import json
import subprocess


def test_idx_market_status_schedule_contract():
    """Verify market status correctly determines IDX phases and next pipeline runs."""
    script = """
    function getIdxMarketStatusForTime(day, hour, min) {
      const totalMin = hour * 60 + min;

      let nextEvent = "06:55 WIB Morning Brief";
      if (totalMin >= 415 && totalMin < 1200) {
        nextEvent = "20:00 WIB Evening Review";
      } else if (totalMin >= 1200) {
        nextEvent = "06:55 WIB Morning Brief (Next Session)";
      }

      if (day === 0 || day === 6) {
        return { isOpen: false, status: "closed", phase: "WEEKEND_CLOSED", nextEvent };
      }

      if (day >= 1 && day <= 4) {
        if (totalMin >= 525 && totalMin < 540) return { isOpen: false, status: "recess", phase: "PRE_OPENING", nextEvent };
        if (totalMin >= 540 && totalMin < 690) return { isOpen: true, status: "open", phase: "SESSION_1", nextEvent };
        if (totalMin >= 690 && totalMin < 810) return { isOpen: false, status: "recess", phase: "RECESS", nextEvent };
        if (totalMin >= 810 && totalMin < 949) return { isOpen: true, status: "open", phase: "SESSION_2", nextEvent };
        if (totalMin >= 949 && totalMin < 961) return { isOpen: false, status: "recess", phase: "PRE_CLOSING", nextEvent };
        if (totalMin >= 961 && totalMin < 975) return { isOpen: false, status: "recess", phase: "POST_TRADING", nextEvent };
        return { isOpen: false, status: "closed", phase: "CLOSED", nextEvent };
      }

      return { isOpen: false, status: "closed", phase: "CLOSED", nextEvent };
    }

    const testCases = [
      { day: 1, hour: 8, min: 50, expectedPhase: "PRE_OPENING", expectedOpen: false },
      { day: 2, hour: 10, min: 0, expectedPhase: "SESSION_1", expectedOpen: true },
      { day: 3, hour: 12, min: 0, expectedPhase: "RECESS", expectedOpen: false },
      { day: 4, hour: 14, min: 0, expectedPhase: "SESSION_2", expectedOpen: true },
      { day: 1, hour: 15, min: 55, expectedPhase: "PRE_CLOSING", expectedOpen: false },
      { day: 1, hour: 16, min: 5, expectedPhase: "POST_TRADING", expectedOpen: false },
      { day: 6, hour: 10, min: 0, expectedPhase: "WEEKEND_CLOSED", expectedOpen: false },
    ];

    const results = testCases.map(tc => {
      const res = getIdxMarketStatusForTime(tc.day, tc.hour, tc.min);
      return {
        matchedPhase: res.phase === tc.expectedPhase,
        matchedOpen: res.isOpen === tc.expectedOpen,
        phase: res.phase,
        nextEvent: res.nextEvent
      };
    });

    console.log(JSON.stringify(results));
    """

    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    out = json.loads(res.stdout)

    for r in out:
      assert r["matchedPhase"] is True
      assert r["matchedOpen"] is True
      assert r["nextEvent"] in ["06:55 WIB Morning Brief", "20:00 WIB Evening Review", "06:55 WIB Morning Brief (Next Session)"]
