import { useState } from "react";
import { detailSchema } from "../api/contracts";
import type { Course, Privacy } from "../api/contracts";
import { useResource } from "../hooks/useResource";
import { Loading, Notice, Panel } from "../components/ui";

type Example = { title: string; learner: string; week: number; check: string };

export function demoExamples(course: Course): Example[] {
  const courseIndexes: Record<string, number> = {
    "synthetic:CS110:2026A:v2": 1,
    "synthetic:DS210:2026A:v2": 2,
    "synthetic:ED220:2026A:v2": 3,
  };
  const index = courseIndexes[course.presentation_id];
  if (course.data_origin !== "synthetic" || !index) return [];
  const examples = [
    {
      title: "Quiet activity, strong assessed grades",
      number: 3,
      week: 6,
      check:
        "Compare activity with published assessed grades and required work. If login monitoring is disabled, quiet activity must not become either a concern or reassurance. Other academic concerns can still apply.",
    },
    {
      title:
        index === 2
          ? "Practice is not a summative grade"
          : "Optional practice is not required work",
      number: 1,
      week: 6,
      check:
        index === 2
          ? "Open Academic records. Practice marks stay separate from assessed grades; optional practice resources are not overdue required work."
          : "Compare required resources with optional practice. Optional practice is not overdue required work. This course has no marked practice quizzes; inspect the Applied Data Project v2 course at week 6 for that comparison.",
    },
    {
      title: "Approved extension",
      number: 6,
      week: 4,
      check:
        "Inspect the approved extension and checkpoint cutoff. An extended assessment is not missed before its effective deadline. This does not excuse unrelated overdue work or guarantee a low risk score.",
    },
    {
      title: "Support and later progress",
      number: 8,
      week: 8,
      check:
        "Open Support record. Compare academic evidence before and after recorded support; keep planned and completed actions distinct. Later improvement does not prove the intervention caused it.",
    },
  ];
  return examples
    .filter((example) => course.checkpoints.includes(example.week))
    .map((example) => ({
      title: example.title,
      check: example.check,
      week: example.week,
      learner: `synthetic:learner:${index}:${String(example.number).padStart(4, "0")}`,
    }));
}

export function DemoGuide({
  course,
  privacy,
  open,
}: {
  course: Course;
  privacy: Privacy;
  open: (learner: string, week: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const examples = demoExamples(course);
  if (!examples.length) return null;
  return (
    <Panel
      title="Synthetic scenario guide"
      note="Fictional scenario design, not model findings or an accuracy claim."
    >
      <details onToggle={(event) => setExpanded(event.currentTarget.open)}>
        <summary>Choose a demonstration record</summary>
        {expanded && (
          <GuideSelection
            key={course.presentation_id}
            examples={examples}
            course={course}
            privacy={privacy}
            open={open}
          />
        )}
        <p>
          This guide is not sent to the predictor. Opening a record never queues
          analysis, edits data or changes course settings.
        </p>
        <h3>Missing-feed check · separate controlled test</h3>
        <p>
          The main demonstration cohort has complete applicable feeds. In
          separate missing-feed tests, absent grades or activity remain
          unavailable, never zero. If essential evidence is insufficient, the
          system abstains without a risk score. Refresh does not create or
          repair missing source records.
        </p>
      </details>
    </Panel>
  );
}

function GuideSelection({
  examples,
  course,
  privacy,
  open,
}: {
  examples: Example[];
  course: Course;
  privacy: Privacy;
  open: (learner: string, week: number) => void;
}) {
  const [selected, setSelected] = useState(0);
  const example = examples[selected] ?? examples[0];
  const path = `v2/courses/${encodeURIComponent(course.presentation_id)}/learners/${encodeURIComponent(example.learner)}?week=${example.week}&privacy=${privacy}`;
  const { data, error } = useResource(path, detailSchema);
  return (
    <div className="editor-form">
      <label>
        Demonstration example
        <select
          aria-label="Demonstration example"
          value={selected}
          onChange={(event) => setSelected(Number(event.target.value))}
        >
          {examples.map((item, index) => (
            <option key={item.title} value={index}>
              {item.title}
            </option>
          ))}
        </select>
      </label>
      <p>{example.check}</p>
      <p>
        Learner ID: {example.learner} · week {example.week}
      </p>
      {error ? (
        <Notice error>
          {error} This scenario may not exist in a smaller or customized cohort.
        </Notice>
      ) : !data ? (
        <Loading />
      ) : !data.snapshot ? (
        <Notice>
          This learner has no prepared snapshot for the demonstration
          checkpoint.
        </Notice>
      ) : (
        <button onClick={() => open(example.learner, example.week)}>
          Open demonstration record
        </button>
      )}
    </div>
  );
}
