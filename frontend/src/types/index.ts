export interface Client {
  id: number;
  business_name: string;
  contact_person: string;
  email: string;
  phone?: string | null;
  preferred_language?: string;

  // Location & Agency
  district?: string | null;
  preferred_districts?: string[];
  preferred_upazilas?: string[];
  preferred_agencies?: string[];

  // Category & Financial
  work_categories?: string[];
  min_project_value_bdt?: number | null;
  max_project_value_bdt?: number | null;

  // Experience & Technical
  years_of_experience?: number | null;
  previous_project_types?: string[];
  similar_work_experience?: string | null;
  approx_annual_turnover_bdt?: number | null;
  available_equipment?: string[];
  available_manpower?: string[];
  licenses_certifications?: string[];
  excluded_areas_or_categories?: string[];

  // Notification & Status
  notification_preference?: string;
  notification_schedules?: string[];
  client_status: 'draft' | 'active' | 'paused';
  is_demo?: boolean;
  experience_notes?: string | null;
  known_constraints?: string | null;

  total_matches?: number;
  created_at?: string;
  updated_at?: string;
}

export interface MatchedTender {
  assessment_id: number;
  tender_id: number;
  official_tender_id: string;
  title: string;
  agency: string;
  office: string;
  district: string;
  location_details?: string | null;
  category: string;
  estimated_value_bdt?: number | null;
  tender_security_bdt?: number | null;
  closing_date?: string | null;
  source_url: string;
  preference_fit_status: 'fits' | 'partial' | 'outside';
  preference_reasons: string[];
  known_mismatches: string[];
  unknown_items_to_verify: string[];
  overall_fit_explanation_bn: string;
}

export interface ClientMatchesResponse {
  client_id: number;
  client_name: string;
  total: number;
  limit: number;
  offset: number;
  matches: MatchedTender[];
}

export interface HealthStatus {
  status: string;
  app: string;
  version: string;
  timestamp: string;
  email_dev_mode: boolean;
  smtp_configured: boolean;
}
