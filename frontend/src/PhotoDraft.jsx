import { useState } from 'react'
import { photoImageUrl } from './api'

const CATEGORIES = ['condition', 'allergy', 'surgery', 'note']

function withSelection(items) {
  return items.map((item) => ({ ...item, include: !item.already_on_file }))
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

  return (
    <div className="draft-card">
      <div className="draft-head">
        <h2>Check what we read from your photo</h2>
        <p className="draft-warning">Nothing is saved to your record until you press Save.</p>
      </div>

      <div className="draft-body">
        <div className="draft-image">
          <img src={photoImageUrl(draft.id)} alt={draft.filename || 'uploaded photo'} />
          <span className="draft-filename">{draft.filename}</span>
        </div>

        <div className="draft-details">
          {draft.error && <p className="draft-error">{draft.error}</p>}

          {draft.summary && <p className="draft-summary">{draft.summary}</p>}

          {nothingFound && (
            <p className="draft-error">
              Nothing recognisable was found in this image. Try a sharper photo, or add the
              details yourself.
            </p>
          )}

          {medications.length > 0 && (
            <section className="draft-section">
              <h3>Medications</h3>
              {medications.map((row, index) => (
                <div className={`draft-row ${row.include ? '' : 'excluded'}`} key={`m-${index}`}>
                  <input
                    type="checkbox"
                    checked={row.include}
                    disabled={busy}
                    onChange={(e) => updateMedication(index, 'include', e.target.checked)}
                  />
                  <div className="draft-fields">
                    <input
                      value={row.medication}
                      disabled={busy}
                      placeholder="Medicine"
                      onChange={(e) => updateMedication(index, 'medication', e.target.value)}
                    />
                    <input
                      value={row.dosage}
                      disabled={busy}
                      placeholder="Dosage"
                      onChange={(e) => updateMedication(index, 'dosage', e.target.value)}
                    />
                    <input
                      value={row.frequency}
                      disabled={busy}
                      placeholder="How often"
                      onChange={(e) => updateMedication(index, 'frequency', e.target.value)}
                    />
                  </div>
                  {row.already_on_file && <span className="draft-badge">already on file</span>}
                </div>
              ))}
            </section>
          )}

          {records.length > 0 && (
            <section className="draft-section">
              <h3>History</h3>
              {records.map((row, index) => (
                <div className={`draft-row ${row.include ? '' : 'excluded'}`} key={`r-${index}`}>
                  <input
                    type="checkbox"
                    checked={row.include}
                    disabled={busy}
                    onChange={(e) => updateRecord(index, 'include', e.target.checked)}
                  />
                  <div className="draft-fields">
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
                    <input
                      value={row.title}
                      disabled={busy}
                      placeholder="What is it"
                      onChange={(e) => updateRecord(index, 'title', e.target.value)}
                    />
                    <input
                      value={row.details}
                      disabled={busy}
                      placeholder="Details"
                      onChange={(e) => updateRecord(index, 'details', e.target.value)}
                    />
                  </div>
                  {row.already_on_file && <span className="draft-badge">already on file</span>}
                </div>
              ))}
            </section>
          )}
        </div>
      </div>

      <div className="draft-actions">
        <button className="ghost" disabled={busy} onClick={() => onDiscard(draft.id)}>
          Discard
        </button>
        <button className="primary" disabled={busy || total === 0} onClick={handleConfirm}>
          {busy ? 'Saving...' : `Save ${total} item${total === 1 ? '' : 's'}`}
        </button>
      </div>
    </div>
  )
}

export default PhotoDraft
