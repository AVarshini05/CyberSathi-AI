import React from 'react';
import { UseFormRegister, FieldErrors } from 'react-hook-form';
import { ComplaintQuestion } from '../../types';

interface DynamicFormProps {
  questions: ComplaintQuestion[];
  register: UseFormRegister<any>;
  errors: FieldErrors<any>;
}

export const DynamicForm: React.FC<DynamicFormProps> = ({
  questions,
  register,
  errors,
}) => {
  if (questions.length === 0) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
      {questions.map((q) => {
        const inputName = `dynamic_${q.id}`;
        const options = q.field_options ? q.field_options.split(',') : [];

        return (
          <div key={q.id} className="flex flex-col">
            <label className="text-xs font-bold text-slate-700 mb-1.5 flex items-center">
              {q.field_label}
              {q.is_required && <span className="text-red-500 ml-0.5">*</span>}
            </label>

            {q.field_type === 'select' ? (
              <select
                {...register(inputName, { required: q.is_required })}
                className={`border rounded-lg p-2.5 text-sm outline-none bg-white focus:border-gov-indigo transition-colors ${
                  errors[inputName] ? 'border-red-500 bg-red-50/20' : 'border-gov-border'
                }`}
              >
                <option value="">-- Choose Option --</option>
                {options.map((opt, i) => (
                  <option key={i} value={opt.trim()}>
                    {opt.trim()}
                  </option>
                ))}
              </select>
            ) : q.field_type === 'textarea' ? (
              <textarea
                {...register(inputName, { required: q.is_required })}
                rows={3}
                placeholder={`Enter ${q.field_label.toLowerCase()}`}
                className={`border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo transition-colors ${
                  errors[inputName] ? 'border-red-500 bg-red-50/20' : 'border-gov-border'
                }`}
              />
            ) : (
              <input
                type={q.field_type}
                {...register(inputName, { required: q.is_required })}
                placeholder={`Enter ${q.field_label.toLowerCase()}`}
                className={`border rounded-lg p-2.5 text-sm outline-none focus:border-gov-indigo transition-colors ${
                  errors[inputName] ? 'border-red-500 bg-red-50/20' : 'border-gov-border'
                }`}
              />
            )}

            {errors[inputName] && (
              <span className="text-[10px] font-semibold text-red-500 mt-1">
                This field is required
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
};
export default DynamicForm;
