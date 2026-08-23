import { useState } from 'react'
import { photoImageUrl } from './api'
import { AlertIcon, CheckIcon, FileTextIcon, ImageIcon, PillIcon } from './icons'

const CATEGORIES = ['condition', 'allergy', 'surgery', 'note']

function withSelection(items) {
  return items.map((item) => ({ ...item, include: !item.already_on_file }))
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  )
}

function PhotoDraft({ draft, busy, onConfirm, onDiscard }) {
  const [medications, setMedications] = useState(() => withSelection(draft.medications || []))
  const [records, setRecords] = useState(() => withSelection(draft.records || []))

  const update = (setter) => (index, field, value) => {
    setter((rows) => rows.map((row, i) => (i === index ? { ...row, [field]: value } : row)))
  }

  const updateMedication = update(setMedications)
  const updateRecord = update(setRecords)

  const chosenMedications = medications.filter((row) => row.include)
  const chosenRecords = records.filter((row) => row.include)
  const total = chosenMedications.length + chosenRecords.length

  const strip = (rows, fields) =>
    rows.map((row) => Object.fromEntries(fields.map((field) => [field, row[field] || ''])))

  const handleConfirm = () => {
    onConfirm(
      draft.id,
      strip(chosenMedications, ['medication', 'dosage', 'frequency', 'notes']),
      strip(chosenRecords, ['category', 'title', 'details']),
    )
  }

  const nothingFound = !draft.error && medications.length === 0 && records.length === 0

  const renderToggle = (row, index, setter) => (
    <label className="toggle">
      <input
        type="checkbox"
        checked={row.include}
        disabled={busy}
        onChange={(e) => setter(index, 'include', e.target.checked)}
      />
      <span className="toggle-box" aria-hidden="true">
        <CheckIcon />
      </span>
      <span className="sr-only">Include this item</span>
    </label>
  )

  return (
    <section className="draft" aria-label="Review what was read from your photo">
      <header className="draft-head">
        <div>
          <h2>From your photo</h2>
          <p>Check the details, then keep what is right. Nothing is saved until you do.</p>
        </div>
        <span className="draft-pill">
          <ImageIcon />
          {draft.filename}
        </span>
      </header>

      <div className="draft-main">
        <figure className="draft-figure">
          <img src={photoImageUrl(draft.id)} alt={draft.filename || 'Uploaded document'} />
        </figure>

        <div className="draft-content">
          {draft.error && (
            <p className="notice danger">
              <AlertIcon />
              {draft.error}
            </p>
          )}

          {nothingFound && (
            <p className="notice danger">
              <AlertIcon />
              Nothing readable was found. Try a sharper, better-lit photo.
            </p>
          )}

          {draft.summary && <p className="draft-summary">{draft.summary}</p>}

          {medications.length > 0 && (
            <div className="group">
              <h3>
                <PillIcon /> Medicines
              </h3>
              {medications.map((row, index) => (
                <div className={`entry ${row.include ? '' : 'off'}`} key={`m-${index}`}>
                  {renderToggle(row, index, updateMedication)}
                  <div className="entry-grid meds">
                    <Field label="Medicine">
                      <input
                        value={row.medication}
                        disabled={busy}
                        onChange={(e) => updateMedication(index, 'medication', e.target.value)}
                      />
                    </Field>
                    <Field label="Dose">
                      <input
                        value={row.dosage}
                        disabled={busy}
                        onChange={(e) => updateMedication(index, 'dosage', e.target.value)}
                      />
                    </Field>
                    <Field label="How often">
                      <input
                        value={row.frequency}
                        disabled={busy}
                        onChange={(e) => updateMedication(index, 'frequency', e.target.value)}
                      />
                    </Field>
                  </div>
                  {row.already_on_file && <span className="tag">On file</span>}
                </div>
              ))}
            </div>
          )}

          {records.length > 0 && (
            <div className="group">
              <h3>
                <FileTextIcon /> History
              </h3>
              {records.map((row, index) => (
                <div className={`entry ${row.include ? '' : 'off'}`} key={`r-${index}`}>
                  {renderToggle(row, index, updateRecord)}
                  <div className="entry-grid recs">
                    <Field label="Type">
                      <select
                        value={row.category}
                        disabled={busy}
                        onChange={(e) => updateRecord(index, 'category', e.target.value)}
                      >
                        {CATEGORIES.map((category) => (
                          <option key={category} value={category}>
                            {category}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="What">
                      <input
                        value={row.title}
                        disabled={busy}
                        onChange={(e) => updateRecord(index, 'title', e.target.value)}
                      />
                    </Field>
                    <Field label="Notes">
                      <input
                        value={row.details}
                        disabled={busy}
                        onChange={(e) => updateRecord(index, 'details', e.target.value)}
                      />
                    </Field>
                  </div>
                  {row.already_on_file && <span className="tag">On file</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <footer className="draft-foot">
        <span className="count">
          {total === 0 ? 'Nothing selected' : `${total} selected`}
        </span>
        <div className="draft-buttons">
          <button type="button" className="btn ghost" disabled={busy} onClick={() => onDiscard(draft.id)}>
            Discard
          </button>
          <button type="button" className="btn primary" disabled={busy || total === 0} onClick={handleConfirm}>
            {busy ? 'Saving…' : 'Save to record'}
          </button>
        </div>
      </footer>
    </section>
  )
}

export default PhotoDraft
