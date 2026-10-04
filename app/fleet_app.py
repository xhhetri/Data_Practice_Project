"""Daily fuel ledger and evidence-linked weekly review for one protected workspace."""
import os
import sys
import hashlib
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')
from src.fleet.store import Repository, GRADES, STATUSES
from src.fleet.analytics import weekly_review, efficiency_intervals, exceptions, observed_rate, scenario, render_weekly_report
from src.fleet.transfers import csv_headers, preview_csv, import_preview, export_csv, backup, restore
from src.fleet.security import validate_config, AuthGate
from src.fleet.demo import seed_demo

st.set_page_config(page_title='Fleet Fuel Review', page_icon='🚐', layout='wide')
data_root = Path(os.environ.get('FLEET_DATA_DIR', str(ROOT / 'data/operational'))).resolve()
mode = os.environ.get('FLEET_MODE', 'local')
stored_hash = os.environ.get('FLEET_PASSWORD_HASH', '')
try:
    protected = validate_config(mode, stored_hash)
except ValueError:
    st.title('Fleet Fuel Review')
    st.error('Access protection is not configured correctly. Ask the operator to set a valid workspace password hash and application mode.')
    st.stop()

if protected:
    gate = AuthGate(data_root / 'authentication.sqlite', stored_hash)
    session = st.session_state.get('auth_session', {})
    if not gate.session_valid(session):
        st.title('Fleet Fuel Review')
        st.write('Sign in to your private vehicle records.')
        with st.form('login'):
            password = st.text_input('Workspace password', type='password', key='login_password', max_chars=256)
            submitted = st.form_submit_button('Sign in', key='sign_in')
        if submitted:
            result = gate.attempt(password)
            if result['ok']:
                st.session_state.clear()
                st.session_state['auth_session'] = gate.new_session()
                st.rerun()
            st.error(f"Sign-in unavailable. Try again in {result['retry_after']} seconds." if result['retry_after'] else 'Password not recognised.')
        st.stop()
    if st.sidebar.button('Sign out', key='sign_out'):
        st.session_state.clear()
        st.rerun()
else:
    st.sidebar.caption('Local workspace · keep this service on your device.')


def navigate(page, record_id=None):
    st.session_state['page'] = page
    if record_id:
        st.session_state['edit_record'] = record_id
        st.session_state.pop('edit_snapshot', None)


def money(cents):
    return f'AUD {Decimal(str(cents))/100:,.2f}'


def display_records(rows, vehicles):
    names = {v['id']: v['name'] for v in vehicles}
    return pd.DataFrame([dict(Date=r['occurred_at'] if r['has_time'] else r['occurred_at'][:10],
                             Vehicle=names.get(r['vehicle_id'], ''), Litres=float(r['litres']),
                             **{'Paid (AUD)': float(Decimal(r['amount_cents'])/100)},
                             Odometer=r['odometer_km'], Tank=r['tank_status'], Reference=r['reference'],
                             Voided=bool(r['void']), Revision=r['revision']) for r in rows])


def purchase_fields(prefix, vehicle_ids, names, defaults=None):
    defaults = defaults or {}
    current = datetime.now(repo.timezone)
    initial = datetime.fromisoformat(defaults.get('occurred_at', current.isoformat()))
    vehicle = st.selectbox('Vehicle', vehicle_ids, format_func=lambda i: names[i],
                           index=vehicle_ids.index(defaults['vehicle_id']) if defaults.get('vehicle_id') in vehicle_ids else 0,
                           key=f'{prefix}_vehicle')
    a, b = st.columns(2)
    day = a.date_input('Purchase date', value=initial.date(), max_value=current.date(), key=f'{prefix}_date')
    clock = b.time_input('Purchase time', value=initial.time().replace(second=0, microsecond=0), key=f'{prefix}_time')
    has_time = st.checkbox('Time is known', value=bool(defaults.get('has_time', True)), key=f'{prefix}_has_time', help='Leave unchecked for date-only records; ambiguous order can prevent efficiency estimates.')
    a, b = st.columns(2)
    litres = a.text_input('Litres purchased', value=defaults.get('litres', ''), key=f'{prefix}_litres', max_chars=20)
    amount = b.text_input('Total paid (AUD)', value=f"{Decimal(defaults['amount_cents'])/100:.2f}" if defaults else '', key=f'{prefix}_amount', max_chars=20)
    a, b = st.columns(2)
    odo = a.text_input('Odometer (km, optional)', value=defaults.get('odometer_km') or '', key=f'{prefix}_odometer', max_chars=20)
    tank = b.selectbox('Tank after purchase', ['unknown', 'partial', 'full'], index=['unknown', 'partial', 'full'].index(defaults.get('tank_status', 'unknown')), key=f'{prefix}_tank')
    with st.expander('Receipt details and completeness'):
        reference = st.text_input('Receipt reference (optional)', value=defaults.get('reference', ''), key=f'{prefix}_reference', max_chars=120)
        vendor = st.text_input('Vendor (optional)', value=defaults.get('vendor', ''), key=f'{prefix}_vendor', max_chars=120)
        note = st.text_area('Note (optional)', value=defaults.get('note', ''), key=f'{prefix}_note', max_chars=2000)
        incomplete = st.checkbox('Some fuel purchases since the preceding entry are missing', value=bool(defaults.get('incomplete', False)), key=f'{prefix}_incomplete')
    return dict(vehicle_id=vehicle, occurred_at=f'{day}T{clock.isoformat()}' if has_time else day.isoformat(),
                litres=litres, amount=amount, odometer_km=odo, tank_status=tank, reference=reference,
                vendor=vendor, note=note, incomplete=incomplete)


with st.sidebar:
    st.title('Fleet Fuel Review')
    workspace_mode = st.radio('Workspace', ['My records', 'Fictional demo'], key='workspace_mode')
    if workspace_mode == 'My records':
        choices = ['records.sqlite', *sorted(p.name for p in data_root.glob('workspace-*.sqlite'))]
        workspace_file = st.selectbox('Record set', choices, key='workspace_file', format_func=lambda p: 'My records' if p == 'records.sqlite' else 'Restored ' + p[10:18])
    else:
        workspace_file = 'demo.sqlite'
    page = st.radio('Go to', ['This week', 'Record fuel', 'Import records', 'Vehicles', 'History and backups'], key='page')
    st.caption('AUD · litres · kilometres. Records remain in this workspace.')

workspace_context = str(data_root / workspace_file)
if st.session_state.get('workspace_context') != workspace_context:
    for key in list(st.session_state):
        if key not in ('auth_session', 'workspace_mode', 'workspace_file', 'page'):
            del st.session_state[key]
    st.session_state['workspace_context'] = workspace_context
repo = Repository(data_root / workspace_file)
if workspace_mode == 'Fictional demo':
    seed_demo(repo)
    st.warning('Fictional demonstration data — practice records, planted cases and changes here are not real savings or research results.')

vehicles = repo.vehicles()
active_vehicles = [v for v in vehicles if not v['archived']]
names = {v['id']: v['name'] for v in vehicles}
today = datetime.now(repo.timezone).date()
if st.session_state.get('flash'):
    st.success(st.session_state.pop('flash'))

if page == 'Vehicles':
    st.title('Your vehicles')
    st.write('Add each vehicle once, then record purchases or import its existing records.')
    with st.form('vehicle_create'):
        name = st.text_input('Vehicle nickname', key='vehicle_name', max_chars=64)
        grade = st.selectbox('Fuel grade', GRADES, key='vehicle_grade')
        tank = st.text_input('Tank capacity (litres, optional)', key='vehicle_capacity', max_chars=20)
        if st.form_submit_button('Add vehicle', key='create_vehicle'):
            try:
                repo.create_vehicle(dict(name=name, fuel_grade=grade, tank_capacity_l=tank))
                st.success('Vehicle added. You can now record fuel.')
                vehicles = repo.vehicles()
            except ValueError as error:
                st.error(str(error))
    if vehicles:
        st.dataframe(pd.DataFrame(vehicles)[['name', 'fuel_grade', 'tank_capacity_l', 'archived']], hide_index=True)
        chosen = st.selectbox('Vehicle to update', [v['id'] for v in vehicles], format_func=lambda i: next(v['name'] for v in vehicles if v['id'] == i))
        snapshot = st.session_state.get('vehicle_snapshot')
        if not snapshot or snapshot['id'] != chosen:
            snapshot = next(v for v in vehicles if v['id'] == chosen)
            st.session_state['vehicle_snapshot'] = snapshot
        prefix = f"vehicle_{chosen}_{snapshot['revision']}"
        if st.button('Reload vehicle details'):
            st.session_state.pop('vehicle_snapshot', None)
            st.rerun()
        with st.form('vehicle_update'):
            updated_name = st.text_input('Nickname', value=snapshot['name'], key=prefix+'_name', max_chars=64)
            updated_grade = st.selectbox('Grade', GRADES, index=GRADES.index(snapshot['fuel_grade']), key=prefix+'_grade')
            capacity = st.text_input('Capacity (litres)', value=snapshot['tank_capacity_l'] or '', key=prefix+'_capacity', max_chars=20)
            archived = st.checkbox('Archive this vehicle', value=bool(snapshot['archived']), key=prefix+'_archived', help='History is retained; new purchases are blocked until restored.')
            if st.form_submit_button('Save vehicle changes'):
                try:
                    repo.update_vehicle(chosen, dict(name=updated_name, fuel_grade=updated_grade, tank_capacity_l=capacity, archived=archived), snapshot['revision'])
                    st.session_state.pop('vehicle_snapshot', None)
                    st.session_state['flash'] = 'Vehicle changes saved.'
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

elif page == 'Record fuel':
    st.title('Record a fuel purchase')
    st.write('Capture the receipt now. Spending is available immediately; valid full-to-full readings support efficiency later.')
    if not active_vehicles:
        st.info('Add your first vehicle before recording fuel.')
        st.button('Add vehicle', on_click=navigate, args=('Vehicles',))
    else:
        st.session_state.setdefault('save_request', str(uuid4()))
        if st.session_state.pop('reset_purchase_form', False):
            for key in list(st.session_state):
                if key.startswith('new_'):
                    del st.session_state[key]
        with st.form('purchase_create'):
            value = purchase_fields('new', [v['id'] for v in active_vehicles], names)
            if st.form_submit_button('Save purchase', key='save_purchase'):
                try:
                    repo.save_purchase(value, st.session_state['save_request'])
                    st.session_state['save_request'] = str(uuid4())
                    st.session_state['reset_purchase_form'] = True
                    st.session_state['flash'] = 'Purchase saved. It is included in your weekly review.'
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))

elif page == 'Import records':
    st.title('Import existing records')
    st.write('Choose columns, inspect a preview, then confirm. Preview does not save records. Maximum 5 MiB / 10,000 rows.')
    st.download_button('Download CSV template', 'vehicle,date,litres,amount,odometer,tank_status,reference\n', 'fuel-import-template.csv', 'text/csv')
    upload = st.file_uploader('Fuel transactions CSV (UTF-8)', type=['csv'], key='import_file')
    if upload and active_vehicles:
        try:
            content = upload.getvalue()
            upload_hash = hashlib.sha256(content).hexdigest()
            if st.session_state.get('import_upload_hash') != upload_hash:
                st.session_state.pop('import_preview', None)
                st.session_state.pop('ack_duplicates', None)
                st.session_state['import_upload_hash'] = upload_hash
            headers = csv_headers(content)
            choice = st.radio('Vehicles in this file', ['Use a vehicle column', 'All rows belong to one vehicle'])
            with st.form('import_mapping'):
                mapping = {}
                if choice == 'Use a vehicle column':
                    mapping['vehicle_id'] = st.selectbox('Vehicle column (nickname or ID)', headers)
                else:
                    mapping['vehicle_id'] = st.selectbox('Vehicle for all rows', [v['id'] for v in active_vehicles], format_func=lambda i: names[i])
                aliases = {'occurred_at': ('date', 'occurred_at'), 'litres': ('litres',), 'amount': ('amount', 'amount_AUD'), 'odometer_km': ('odometer', 'odometer_km'), 'tank_status': ('tank_status',), 'incomplete': ('missing_purchases',), 'reference': ('reference',), 'vendor': ('vendor',), 'note': ('note',)}
                for field, guesses in aliases.items():
                    required = field in ('occurred_at', 'litres', 'amount')
                    options = headers if required else ['Not supplied', *headers]
                    found = next((h for h in headers if h in guesses), options[0])
                    column = st.selectbox(field.replace('_', ' ').capitalize() + ' column', options, index=options.index(found))
                    if column != 'Not supplied':
                        mapping[field] = column
                if st.form_submit_button('Preview import'):
                    st.session_state['import_preview'] = preview_csv(content, mapping, vehicles, repo.purchases(True), repo.timezone.key)
                    st.session_state['import_workspace'] = workspace_file
            p = st.session_state.get('import_preview')
            if p and st.session_state.get('import_workspace') == workspace_file:
                st.subheader('Preview · nothing saved yet')
                st.write(f"{len(p['rows'])} valid rows; {len(p['errors'])} errors; {len(p['warnings'])} matching-record warnings.")
                preview_frame = pd.DataFrame(p['rows']).head(100)
                if not preview_frame.empty:
                    preview_frame['vehicle_id'] = preview_frame['vehicle_id'].map(names)
                    preview_frame = preview_frame.rename(columns={'vehicle_id': 'Vehicle'})
                st.dataframe(preview_frame, hide_index=True)
                st.caption('Confirmation saves exactly these previewed rows. Generate a new preview after changing the column mapping.')
                if p['errors']:
                    st.error('Correct every error and generate a new preview.')
                    st.dataframe(pd.DataFrame(p['errors']), hide_index=True)
                if p['warnings']:
                    st.warning('Review potential duplicates. Existing purchases will be retained.')
                    st.dataframe(pd.DataFrame(p['warnings']), hide_index=True)
                acknowledge = st.checkbox('I reviewed the matching purchases and want to import these rows', key='ack_duplicates') if p['warnings'] else False
                if st.button('Confirm previewed rows', disabled=bool(p['errors'])):
                    imported = import_preview(repo, p, acknowledge)
                    st.session_state.pop('import_preview', None)
                    st.success(f'{len(imported)} rows recorded. Retrying this same file/mapping returns the original import.')
        except ValueError as error:
            st.error(str(error))
    elif not upload:
        st.session_state.pop('import_preview', None)
        st.session_state.pop('import_upload_hash', None)
    elif not active_vehicles:
        st.info('Add vehicles first so imported rows can be matched to known vehicles.')

elif page == 'History and backups':
    st.title('Records and recovery')
    all_rows = repo.purchases(True)
    st.download_button('Download all records (CSV)', export_csv(all_rows, vehicles), 'fleet-purchases.csv', 'text/csv')
    st.download_button('Download workspace backup', backup(repo), 'fleet-workspace-backup.json', 'application/json')
    st.caption('The JSON backup includes vehicles, purchases, corrections, import identities and review history. Keep it in a private location.')
    if all_rows:
        st.dataframe(display_records(list(reversed(all_rows)), vehicles), hide_index=True)
        selected = st.selectbox('Purchase to inspect or correct', [r['id'] for r in reversed(all_rows)], format_func=lambda i: next(f"{r['occurred_at'][:10]} · {names[r['vehicle_id']]} · {money(r['amount_cents'])}{' · voided' if r['void'] else ''}" for r in all_rows if r['id'] == i), key='edit_record')
        snapshot = st.session_state.get('edit_snapshot')
        if not snapshot or snapshot['id'] != selected:
            snapshot = next(r for r in all_rows if r['id'] == selected)
            st.session_state['edit_snapshot'] = snapshot
        if st.button('Reload purchase details'):
            st.session_state.pop('edit_snapshot', None)
            st.rerun()
        prefix = f"edit_{selected}_{snapshot['revision']}"
        with st.form('purchase_update'):
            value = purchase_fields(prefix, [v['id'] for v in vehicles], names, snapshot)
            if st.form_submit_button('Save correction'):
                try:
                    repo.update_purchase(selected, value, snapshot['revision'])
                    st.session_state.pop('edit_snapshot', None)
                    st.session_state['flash'] = 'Correction saved with its previous version in history.'
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
        ack = st.checkbox('I confirm this record should be restored' if snapshot['void'] else 'I confirm this record should be excluded from active totals', key=prefix+'_confirm')
        if st.button('Restore record' if snapshot['void'] else 'Void record', disabled=not ack):
            try:
                repo.void_purchase(selected, snapshot['revision'], void=not bool(snapshot['void']))
                st.session_state.pop('edit_snapshot', None)
                st.session_state['flash'] = 'Record state changed. All earlier versions are retained.'
                st.rerun()
            except ValueError as error:
                st.error(str(error))
    with st.expander('Change history'):
        events = repo.history()
        st.dataframe(pd.DataFrame(events)[['at_utc', 'entity', 'action', 'record_id']] if events else pd.DataFrame(), hide_index=True)
    with st.expander('Restore a backup into a separate record set'):
        st.write('Your current records remain available. A successful restore creates a separate record set selectable in the sidebar.')
        uploaded = st.file_uploader('Workspace JSON backup', type=['json'], key='restore_file')
        confirm = st.checkbox('Create a separate record set from this backup')
        if st.button('Restore separate record set', disabled=not uploaded or not confirm):
            try:
                result = restore(uploaded.getvalue(), data_root)
                st.success('Backup restored. Select “Restored '+result.name[10:18]+'” in the sidebar.')
            except ValueError as error:
                st.error(str(error))

else:
    st.title('What needs review this week?')
    st.write('Review new spending, check the evidence, and record what you found.')
    if not vehicles:
        st.info('Add your first vehicle, then record a purchase or import your existing spreadsheet. Your real workspace starts empty.')
        st.button('Add vehicle', on_click=navigate, args=('Vehicles',), type='primary')
        st.stop()
    a, b = st.columns(2)
    week = a.date_input('Week containing', value=today, max_value=today, key='review_week')
    vehicle_filter = b.selectbox('Review scope', ['all', *names], format_func=lambda i: 'All vehicles' if i == 'all' else names[i], key='review_scope')
    records = repo.purchases()
    scoped = records if vehicle_filter == 'all' else [r for r in records if r['vehicle_id'] == vehicle_filter]
    review = weekly_review(scoped, vehicles, week, today)
    st.caption(f"{review['start']} to {review['end']} · {'partial week; comparison uses the same elapsed days' if review['partial_week'] else 'complete week'} · recorded purchases")
    all_findings = exceptions(scoped, vehicles)
    saved_reviews = repo.reviews()
    outcomes = {r['id']: r for r in saved_reviews}
    open_findings = [e for e in all_findings if outcomes.get(e['id'], {}).get('status', 'open') in ('open', 'follow-up needed')]
    st.subheader(f'{len(open_findings)} items need review')
    if not open_findings:
        st.info('No rules currently flag these supplied records. This does not prove the records are complete or problem-free.')
    for e in open_findings:
        with st.expander(f"{names[e['vehicle_id']]} · {e['rule'].replace('_', ' ')} · {e['date']}"):
            st.text(e['message'])
            if e.get('baseline'):
                st.write(f"Recorded rate {Decimal(e['rate']):.2f} L/100 km; earlier median {Decimal(e['baseline']):.2f}; {e['earlier_intervals']} earlier intervals.")
                st.caption(e['threshold'])
            evidence = [r for r in records if r['id'] in e['source_ids']]
            st.dataframe(display_records(evidence, vehicles), hide_index=True)
            st.button('Open latest evidence record', key=e['id']+'_open', on_click=navigate, args=('History and backups', evidence[-1]['id']))
            prior = outcomes.get(e['id'], {})
            token_key = 'outcome_token_'+e['id']
            if token_key not in st.session_state:
                st.session_state[token_key] = prior.get('updated_at')
            if st.button('Reload review outcome', key=e['id']+'_reload'):
                st.session_state.pop(token_key, None)
                st.rerun()
            with st.form('outcome_'+e['id']):
                status = st.selectbox('Review outcome', STATUSES, index=STATUSES.index(prior.get('status', 'open')))
                note = st.text_area('What did you find?', value=prior.get('note', ''), max_chars=2000)
                refund = st.text_input('Confirmed refund (AUD, optional)', value=f"{Decimal(prior.get('refund_cents',0))/100:.2f}")
                reference = st.text_input('Refund evidence reference', value=prior.get('refund_reference', ''), max_chars=120)
                if st.form_submit_button('Save review outcome'):
                    try:
                        repo.save_review(dict(id=e['id'], status=status, note=note, refund_amount=refund or '0', refund_reference=reference),
                                         expected_updated_at=st.session_state[token_key])
                        st.session_state.pop(token_key, None)
                        st.session_state['flash'] = 'Review outcome saved. A flag is not counted as a saving.'
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))
    stale = [r for r in saved_reviews if r['id'] not in {e['id'] for e in exceptions(records, vehicles)}]
    if stale:
        with st.expander('Earlier reviews whose evidence has changed'):
            st.caption('Record corrections or new baselines changed these findings. The earlier outcomes remain as history and do not resolve new findings.')
            st.dataframe(pd.DataFrame(stale)[['status', 'note', 'updated_at']], hide_index=True)
    st.subheader('Recorded spending')
    a, b, c = st.columns(3)
    a.metric('Paid this period', money(review['current']['amount_cents']), money(review['change_cents'])+' vs comparison', delta_color='off')
    b.metric('Litres purchased', f"{Decimal(review['current']['litres']):,.3f}")
    c.metric('Receipts recorded', str(review['current']['receipt_count']))
    if review['decomposition']:
        parts = review['decomposition']
        st.write(f"Of the spending change, {money(parts['volume_cents'])} relates to purchase volume and {money(parts['price_cents'])} to the paid price mix. Display rounding can affect the sum by a cent.")
    else:
        st.caption('Price/volume explanation needs recorded purchases in both comparison periods.')
    st.caption(review['caveat'])
    st.download_button('Download weekly review', render_weekly_report(review, vehicles, saved_reviews), f"fuel-review-{review['start']}.md", 'text/markdown')
    st.download_button('Download this period (CSV)', export_csv(review['records'], vehicles), f"fuel-records-{review['start']}.csv", 'text/csv')
    st.button('Record another purchase', on_click=navigate, args=('Record fuel',), type='primary')
    if review['records']:
        frame = display_records(review['records'], vehicles)
        figure = px.bar(frame, x='Date', y='Paid (AUD)', color='Vehicle', title='Recorded purchases in this period')
        figure.update_yaxes(rangemode='tozero')
        st.plotly_chart(figure, width='stretch')
        st.dataframe(frame, hide_index=True)
    with st.expander('Supported efficiency intervals and unavailable estimates'):
        st.dataframe(pd.DataFrame(review['intervals']), hide_index=True)
        for w in review['warnings']:
            st.text(f"{names[w['vehicle_id']]}: {w['reason']} ({w['start']} to {w['end']})")
        if not review['intervals']:
            st.info('No supported interval ends in this period. Record full-tank boundaries and odometers; spending remains available.')
    with st.expander('Plan fuel costs from explicit assumptions'):
        chosen = st.selectbox('Vehicle for scenario', list(names), format_func=lambda i: names[i])
        observed = observed_rate([r for r in records if r['vehicle_id'] == chosen])
        if observed:
            st.caption(f'Distance-weighted rate across all supported recorded intervals: {Decimal(observed):.2f} L/100 km. You can change this assumption.')
        with st.form('scenario'):
            km = st.text_input('Planned kilometres', value='500')
            rate = st.text_input('Assumed fuel rate (L/100 km)', value=f'{Decimal(observed):.3f}' if observed else '')
            a, b, c = st.columns(3)
            low = a.text_input('Low price (AUD/L)', value='1.80')
            base = b.text_input('Base price (AUD/L)', value='2.00')
            high = c.text_input('High price (AUD/L)', value='2.20')
            if st.form_submit_button('Calculate scenarios'):
                try:
                    value = scenario(km, rate, [low, base, high])
                    st.write(f"Assumed fuel needed: {value['litres']} L. Low/base/high costs: AUD " + ' / '.join(value['costs']))
                    st.caption(value['caveat'])
                except ValueError as error:
                    st.error(str(error))

st.caption('Review flags identify records to inspect. They do not establish faults, theft, policy effects or achieved savings.')
