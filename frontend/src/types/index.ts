export interface User {
  id: number;
  email: string | null;
  mobile_number: string;
  full_name: string;
  role: 'citizen' | 'officer' | 'admin';
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface ComplaintCategory {
  id: number;
  name: string;
  code: string;
  description: string | null;
}

export interface ComplaintSubcategory {
  id: number;
  category_id: number;
  name: string;
  description: string | null;
}

export interface ComplaintQuestion {
  id: number;
  subcategory_id: number;
  field_name: string;
  field_label: string;
  field_type: string;
  is_required: boolean;
  field_options: string | null;
}

export interface ComplaintAnswer {
  id: number;
  question_id: number;
  value: string;
  field_name?: string;
  field_label?: string;
}

export interface EvidenceFile {
  id: number;
  file_name: string;
  file_type: string;
  file_size: number;
  uploaded_at: string;
}

export interface ComplaintStatus {
  id: number;
  status: string;
  remarks: string | null;
  updated_by: number | null;
  updated_at: string;
}

export interface SuspectReport {
  id: number;
  complaint_id?: number;
  suspect_name: string | null;
  suspect_mobile: string | null;
  suspect_email: string | null;
  suspect_url: string | null;
  suspect_upi: string | null;
  suspect_social_handle: string | null;
  details: string | null;
  created_at: string;
}

export interface Complaint {
  id: number;
  acknowledgement_number: string;
  user_id: number | null;
  category_id: number;
  subcategory_id: number;
  is_anonymous: boolean;
  victim_name: string | null;
  victim_mobile: string | null;
  victim_email: string | null;
  victim_gender: string | null;
  victim_address: string | null;
  victim_state: string | null;
  fraud_description: string;
  current_status: string;
  submission_timestamp: string;
  created_at: string;

  category: ComplaintCategory;
  subcategory: ComplaintSubcategory;
  answers: ComplaintAnswer[];
  evidence_files: EvidenceFile[];
  status_history: ComplaintStatus[];
  suspect_reports: SuspectReport[];
}

export interface SuspectSearchResult {
  query: string;
  report_count: number;
  risk_level: string;
  recent_reports: SuspectReport[];
}

export interface DashboardStats {
  total_complaints: number;
  open_complaints: number;
  closed_complaints: number;
  draft_complaints: number;
}
