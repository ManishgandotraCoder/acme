import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { buildEmployee, meta } from '@/test/fixtures'
import { renderWithProviders } from '@/test/render'
import { EmployeeForm } from './EmployeeForm'

describe('EmployeeForm (create)', () => {
  it('submits a typed payload when valid', async () => {
    const onSubmit = vi.fn()
    const { user } = renderWithProviders(<EmployeeForm meta={meta} onSubmit={onSubmit} />)

    await user.type(screen.getByLabelText(/full name/i), 'Grace Hopper')
    await user.type(screen.getByLabelText(/email/i), 'grace@example.com')
    await user.type(screen.getByRole('textbox', { name: /job title/i }), 'Software Engineer')
    await user.type(screen.getByRole('textbox', { name: /department/i }), 'Engineering')
    await user.click(screen.getByRole('textbox', { name: /country/i }))
    await user.click(screen.getByRole('option', { name: 'India' }))
    await user.type(screen.getByLabelText(/annual salary/i), '2400000')
    await user.type(screen.getByLabelText(/hire date/i), '2021-03-01')
    await user.click(screen.getByRole('button', { name: /save/i }))

    expect(onSubmit).toHaveBeenCalledWith({
      full_name: 'Grace Hopper',
      email: 'grace@example.com',
      job_title: 'Software Engineer',
      department: 'Engineering',
      country: 'India',
      annual_salary: 2400000,
      hire_date: '2021-03-01',
    })
  })

  it('shows the local currency for the chosen country', async () => {
    const { user } = renderWithProviders(<EmployeeForm meta={meta} onSubmit={vi.fn()} />)

    await user.click(screen.getByRole('textbox', { name: /country/i }))
    await user.click(screen.getByRole('option', { name: 'India' }))

    expect(screen.getByLabelText(/annual salary \(INR\)/i)).toBeInTheDocument()
  })

  it('blocks submission and explains what is wrong', async () => {
    const onSubmit = vi.fn()
    const { user } = renderWithProviders(<EmployeeForm meta={meta} onSubmit={onSubmit} />)

    await user.type(screen.getByLabelText(/email/i), 'not-an-email')
    await user.click(screen.getByRole('button', { name: /save/i }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByText('Full name is required')).toBeInTheDocument()
    expect(screen.getByText('Enter a valid email')).toBeInTheDocument()
    expect(screen.getByText('Salary must be greater than 0')).toBeInTheDocument()
  })
})

describe('EmployeeForm (edit)', () => {
  it('submits only changed fields', async () => {
    const onSubmit = vi.fn()
    const { user } = renderWithProviders(
      <EmployeeForm meta={meta} employee={buildEmployee()} onSubmit={onSubmit} />,
    )

    const title = screen.getByRole('textbox', { name: /job title/i })
    await user.clear(title)
    await user.type(title, 'Staff Engineer')
    await user.click(screen.getByRole('button', { name: /save/i }))

    expect(onSubmit).toHaveBeenCalledWith({ job_title: 'Staff Engineer' })
  })

  it('asks for a reason when the salary changes and includes it', async () => {
    const onSubmit = vi.fn()
    const { user } = renderWithProviders(
      <EmployeeForm meta={meta} employee={buildEmployee()} onSubmit={onSubmit} />,
    )
    expect(screen.queryByLabelText(/reason/i)).not.toBeInTheDocument()

    const salary = screen.getByLabelText(/annual salary/i)
    await user.clear(salary)
    await user.type(salary, '88000')
    await user.type(screen.getByLabelText(/reason/i), 'Annual review')
    await user.click(screen.getByRole('button', { name: /save/i }))

    expect(onSubmit).toHaveBeenCalledWith({
      annual_salary: 88000,
      salary_change_reason: 'Annual review',
    })
  })
})
