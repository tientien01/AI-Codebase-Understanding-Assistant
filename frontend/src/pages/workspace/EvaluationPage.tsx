import { InDevelopmentInline, ListRow, Metric, PageTitle, Panel } from '../../components/common/ui'

export function EvaluationPage() {
  const questions = ['Where is login implemented?', 'Which files are related to authentication?', 'What happens if User model changes?', 'Explain restaurant recommendation flow.']
  return (
    <div>
      <PageTitle title="Evaluation" subtitle="Measure answer groundedness, citation coverage, retrieval precision, and failed questions." />
      <div className="evaluation-grid">
        <Panel title="Benchmark Questions">
          {questions.map((question) => <ListRow key={question} title={question} detail="Pending evaluation runner." meta="not run" />)}
        </Panel>
        <Panel title="Metrics">
          <Metric label="Answer groundedness" value="-" />
          <Metric label="Citation coverage" value="-" />
          <Metric label="Retrieval precision" value="-" />
          <Metric label="Average latency" value="-" />
          <InDevelopmentInline text="Evaluation backend is dang phat trien." />
        </Panel>
      </div>
    </div>
  )
}
